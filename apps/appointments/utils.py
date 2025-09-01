from datetime import datetime, timedelta, time, date
from django.utils.timezone import make_aware
from django.utils import timezone

def _time_ranges_minus_lunch(start: time, end: time, lunch_start: time | None, lunch_end: time | None):
    """
    Retorna uma lista de janelas [(start,end), ...] excluindo o almoço, se houver.
    """
    if lunch_start and lunch_end:
        return [(start, lunch_start), (lunch_end, end)]
    return [(start, end)]


def _iter_slots(day_start_dt: datetime, day_end_dt: datetime, step_minutes: int):
    step = timedelta(minutes=step_minutes)
    cur = day_start_dt
    while cur + step <= day_end_dt:
        yield cur
        cur += step


def get_applicable_schedule(funcionario, dia: date):
    """
    Retorna: (start, end, lunch_start, lunch_end, slot_interval_minutes) já resolvidos
    considerando exceção > semanal > defaults.
    """
    tzname = getattr(getattr(funcionario.loja, 'agendamento_config', None), 'timezone_name', 'America/Fortaleza')
    tz = timezone.pytz.timezone(tzname) if hasattr(timezone, 'pytz') else timezone.get_current_timezone()

    # 1) Exceção do dia (se existir)
    exc = funcionario.agendas_excecoes.filter(data=dia).first()
    if exc:
        if exc.is_day_off:
            return None  # sem agenda nesse dia
        # Horários (se não definidos, herdam semanal)
        weekly = funcionario.agendas_semanais.filter(weekday=dia.weekday(), ativo=True).first()
        if not weekly:
            # Sem semanal e sem (inicio,fim) na exceção => sem agenda
            if not (exc.inicio and exc.fim):
                return None
        start = exc.inicio or (weekly.inicio if weekly else None)
        end = exc.fim or (weekly.fim if weekly else None)
        lunch_s = exc.almoco_inicio if exc.almoco_inicio else (weekly.almoco_inicio if weekly else None)
        lunch_e = exc.almoco_fim if exc.almoco_fim else (weekly.almoco_fim if weekly else None)

        interval = (
            exc.slot_interval_minutes
            or (weekly.slot_interval_minutes if weekly and weekly.slot_interval_minutes else None)
            or getattr(getattr(funcionario.loja, 'agendamento_config', None), 'slot_interval_minutes', 15)
        )

        if not (start and end):
            return None
        return (start, end, lunch_s, lunch_e, interval, tz)

    # 2) Agenda semanal
    weekly = funcionario.agendas_semanais.filter(weekday=dia.weekday(), ativo=True).first()
    if not weekly:
        return None

    interval = (
        weekly.slot_interval_minutes
        or getattr(getattr(funcionario.loja, 'agendamento_config', None), 'slot_interval_minutes', 15)
    )
    return (weekly.inicio, weekly.fim, weekly.almoco_inicio, weekly.almoco_fim, interval, tz)


def gerar_slots_disponiveis(funcionario, dia: date, duracao_minutos: int) -> list[datetime]:
    """
    Gera a lista de *inícios de slots* (timezone-aware) onde é possível encaixar um atendimento
    de `duracao_minutos` para o `funcionario` no dia `dia`.

    - Respeita agenda semanal, exceções e almoço.
    - Usa intervalo de slot da exceção/semanal/loja, nessa ordem.
    - Exclui janelas que conflitam com agendamentos existentes.
    """
    sched = get_applicable_schedule(funcionario, dia)
    if not sched:
        return []
    start_t, end_t, lunch_s, lunch_e, step_min, tz = sched

    # 1) Constrói janelas do dia (manhã/tarde) excluindo almoço
    windows = _time_ranges_minus_lunch(start_t, end_t, lunch_s, lunch_e)

    # 2) Busca agendamentos existentes para o funcionário no dia
    from .models import Agendamento

    existing_qs = Agendamento.objects.filter(funcionario=funcionario, data=dia)
    existing: list[tuple[datetime, datetime]] = []
    for ag in existing_qs.prefetch_related("servicos"):
        ag_start = make_aware(datetime.combine(ag.data, ag.hora), timezone=tz)
        dur = sum(ag.servicos.values_list("duracao_minutos", flat=True))
        ag_end = ag_start + timedelta(minutes=dur)
        existing.append((ag_start, ag_end))

    # 3) Gera slots brutos e remove os que conflitam
    slots_ok = []

    for w_start_t, w_end_t in windows:
        w_start = make_aware(datetime.combine(dia, w_start_t), timezone=tz)
        w_end = make_aware(datetime.combine(dia, w_end_t), timezone=tz)

        for s in _iter_slots(w_start, w_end, step_min):
            slot_end = s + timedelta(minutes=duracao_minutos)
            # slot deve caber dentro da janela
            if slot_end > w_end:
                continue

            # checa conflito com agendamentos existentes
            conflita = any(e_start < slot_end and e_end > s for e_start, e_end in existing)

            if not conflita:
                slots_ok.append(s)

    return slots_ok
