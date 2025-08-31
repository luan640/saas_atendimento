from datetime import datetime, timedelta, time, date
from django.utils.timezone import make_aware
from django.utils import timezone
from typing import List


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

    # Se o funcionário tiver dias da semana definidos e o dia não estiver incluso, não há agenda
    dias_cfg = getattr(funcionario, 'dias_semana', '') or ''
    if dias_cfg:
        try:
            dias_lista = [int(d) for d in dias_cfg.split(',') if d != '']
        except ValueError:
            dias_lista = []
        if dia.weekday() not in dias_lista:
            return None

    print(dias_cfg)

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
            or getattr(funcionario, 'slot_interval_minutes', None)
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
        or getattr(funcionario, 'slot_interval_minutes', None)
        or getattr(getattr(funcionario.loja, 'agendamento_config', None), 'slot_interval_minutes', 15)
    )

    return (weekly.inicio, weekly.fim, weekly.almoco_inicio, weekly.almoco_fim, interval, tz)


def gerar_slots_disponiveis(funcionario, dia: date, duracao_minutos: int) -> List[datetime]:
    """
    Usa somente: Funcionario.dias_semana e Funcionario.slot_interval_minutes.
    Janela do dia vem da loja (se existir) ou defaults 09:00–18:00.
    Conflitos via Agendamento somando servicos.duracao_minutos.
    """
    sched = get_applicable_schedule(funcionario, dia)
    if not sched:
        return []

    start_t, end_t, lunch_s, lunch_e, step_min, tz = sched
    atendimento_min = max(int(duracao_minutos or 0), step_min)  # ocupa ao menos 1 slot

    # 1) janelas (manhã/tarde)
    windows = _time_ranges_minus_lunch(start_t, end_t, lunch_s, lunch_e)

    # 2) agendamentos existentes (do dia) somando duração dos serviços
    from .models import Agendamento  # ajuste se o path for outro
    qs = (Agendamento.objects
          .filter(funcionario=funcionario, data=dia)
          .prefetch_related('servicos'))

    existentes = []
    for ag in qs:
        ag_start = make_aware(datetime.combine(ag.data, ag.hora), timezone=tz)
        # soma durações; se não tiver, assume 1 slot
        dur = sum((s.duracao_minutos or 0) for s in ag.servicos.all())
        if dur <= 0:
            dur = step_min
        ag_end = ag_start + timedelta(minutes=dur)
        existentes.append((ag_start, ag_end))

    # 3) gera slots e filtra conflitos
    slots_ok = []
    for w_start_t, w_end_t in windows:
        w_start = make_aware(datetime.combine(dia, w_start_t), timezone=tz)
        w_end   = make_aware(datetime.combine(dia, w_end_t), timezone=tz)

        for s in _iter_slots(w_start, w_end, step_min):
            slot_end = s + timedelta(minutes=atendimento_min)
            if slot_end > w_end:
                continue
            # conflito: (e_start < slot_end) & (e_end > s)
            if not any(e_start < slot_end and e_end > s for (e_start, e_end) in existentes):
                slots_ok.append(s)

    # 4) se dia=hoje, não mostrar horários passados
    now_local = timezone.localtime(timezone.now(), tz)
    if dia == now_local.date():
        slots_ok = [dt for dt in slots_ok if dt >= now_local]

    return slots_ok
