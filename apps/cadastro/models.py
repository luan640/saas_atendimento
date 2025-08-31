from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, RegexValidator
from django.utils.text import slugify

User = settings.AUTH_USER_MODEL

# ----- Lojas -------

class Loja(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lojas',
        limit_choices_to={'is_owner': True}
    )
    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField(max_length=200, blank=True)
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nome)
            slug = base or 'loja'
            i = 1
            while Loja.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_public_path(self):
        return reverse('cadastro:client_start_loja', args=[self.slug])

    def get_public_url(self, request=None):
        path = self.get_public_path()
        if request:
            return request.build_absolute_uri(path)
        return path

    def __str__(self):
        return f"{self.nome} ({self.owner.email})"

# --- Funcionários ---

class Funcionario(models.Model):
    class Cargo(models.TextChoices):
        BARBEIRO = 'barbeiro', 'Barbeiro'
        CABELEIREIRO = 'cabeleireiro', 'Cabeleireiro(a)'
        MANICURE = 'manicure', 'Manicure/Pedicure'
        ESTETICISTA = 'esteticista', 'Esteticista'
        SOMBRANCELHA = 'sobrancelha', 'Designer de Sobrancelha'
        RECEPCAO = 'recepcao', 'Recepção'
        OUTRO = 'outro', 'Outro'

    phone_regex = RegexValidator(
        r'^\+?\d{10,15}$',
        'Informe telefone no formato internacional, ex.: +5585...'
    )

    loja = models.ForeignKey('Loja', on_delete=models.CASCADE, related_name='funcionarios')
    nome = models.CharField(max_length=120)
    cargo = models.CharField(max_length=20, choices=Cargo.choices, default=Cargo.BARBEIRO)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=17, blank=True, null=True, validators=[phone_regex])
    slug = models.SlugField(max_length=160, blank=True)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nome) or 'funcionario'
            tentativa = base
            i = 1
            while Funcionario.objects.filter(loja=self.loja, slug=tentativa).exclude(pk=self.pk).exists():
                i += 1
                tentativa = f'{base}-{i}'
            self.slug = tentativa
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} – {self.loja.nome}'

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        unique_together = (('loja', 'slug'),)
        ordering = ('nome',)

# --- CONFIG POR LOJA (define o intervalo padrão dos slots) ---
class LojaAgendamentoConfig(models.Model):
    loja = models.OneToOneField('Loja', on_delete=models.CASCADE, related_name='agendamento_config')
    slot_interval_minutes = models.PositiveSmallIntegerField(
        default=15,
        help_text='Intervalo padrão entre slots (min). Ex.: 15, 20, 30.'
    )
    timezone_name = models.CharField(
        max_length=64, default=getattr(settings, 'TIME_ZONE', 'America/Fortaleza'),
        help_text='Fuso horário da loja (ex.: America/Fortaleza)'
    )

    def __str__(self):
        return f'Config agendamento – {self.loja.nome} ({self.slot_interval_minutes} min)'

# --- AGENDA SEMANAL DO FUNCIONÁRIO ---
class FuncionarioAgendaSemanal(models.Model):
    class DiaSemana(models.IntegerChoices):
        SEGUNDA = 0, 'Segunda'
        TERCA   = 1, 'Terça'
        QUARTA  = 2, 'Quarta'
        QUINTA  = 3, 'Quinta'
        SEXTA   = 4, 'Sexta'
        SABADO  = 5, 'Sábado'
        DOMINGO = 6, 'Domingo'

    funcionario = models.ForeignKey('Funcionario', on_delete=models.CASCADE, related_name='agendas_semanais')
    weekday = models.PositiveSmallIntegerField(choices=DiaSemana.choices)

    # Janela principal de trabalho (ex.: 10:00 às 19:00)
    inicio = models.TimeField()
    fim = models.TimeField()

    # Intervalo de almoço/descanso (opcional). Se preenchido, será excluído dos slots.
    almoco_inicio = models.TimeField(blank=True, null=True)
    almoco_fim = models.TimeField(blank=True, null=True)

    ativo = models.BooleanField(default=True)

    # (Opcional) Permite sobrescrever o intervalo de slot por funcionário/dia
    slot_interval_minutes = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
        unique_together = (('funcionario', 'weekday'),)
        ordering = ('funcionario', 'weekday')

    def clean(self):
        if self.inicio >= self.fim:
            raise ValidationError('O horário de início deve ser antes do horário de fim.')
        if (self.almoco_inicio and not self.almoco_fim) or (self.almoco_fim and not self.almoco_inicio):
            raise ValidationError('Preencha ambos os horários de almoço/descanso ou deixe ambos em branco.')
        if self.almoco_inicio and self.almoco_fim:
            if not (self.inicio < self.almoco_inicio < self.almoco_fim < self.fim):
                raise ValidationError('O intervalo de almoço deve estar dentro do horário de trabalho.')

    def __str__(self):
        ds = self.get_weekday_display()
        return f'{self.funcionario.nome} – {ds} {self.inicio}-{self.fim}'

# --- EXCEÇÕES ESPECÍFICAS POR DATA ---
class FuncionarioAgendaExcecao(models.Model):
    """
    Permite ajustar um dia específico:
    - is_day_off=True => folga/feriado (sem atendimento).
    - Ou definir janelas especiais e/ou almoço específico só para essa data.
    """
    funcionario = models.ForeignKey('Funcionario', on_delete=models.CASCADE, related_name='agendas_excecoes')
    data = models.DateField()
    is_day_off = models.BooleanField(default=False)

    # Se quiser horário diferente do semanal:
    inicio = models.TimeField(blank=True, null=True)
    fim = models.TimeField(blank=True, null=True)

    almoco_inicio = models.TimeField(blank=True, null=True)
    almoco_fim = models.TimeField(blank=True, null=True)

    slot_interval_minutes = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
        unique_together = (('funcionario', 'data'),)
        ordering = ('funcionario', 'data')

    def clean(self):
        if self.is_day_off:
            # Se é folga, não precisa de horários
            return
        if self.inicio and self.fim and self.inicio >= self.fim:
            raise ValidationError('O horário de início deve ser antes do horário de fim (exceção).')
        if (self.almoco_inicio and not self.almoco_fim) or (self.almoco_fim and not self.almoco_inicio):
            raise ValidationError('Preencha ambos os horários de almoço/descanso ou deixe ambos em branco (exceção).')
        if self.inicio and self.fim and self.almoco_inicio and self.almoco_fim:
            if not (self.inicio < self.almoco_inicio < self.almoco_fim < self.fim):
                raise ValidationError('O intervalo de almoço (exceção) deve estar dentro do horário do dia.')
        # Se não é folga e não há (inicio,fim), cairemos no padrão semanal.
        # Isso é útil para só alterar o almoço ou o intervalo de slot da data.

    def __str__(self):
        flag = 'Folga' if self.is_day_off else 'Especial'
        return f'{self.funcionario.nome} – {self.data} ({flag})'

# ------ Serviços -----

class Servico(models.Model):
    loja = models.ForeignKey(Loja, on_delete=models.CASCADE, related_name='servicos')

    nome = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, blank=True)

    descricao = models.TextField(blank=True)
    duracao_minutos = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)], default=30)
    preco = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    profissionais = models.ManyToManyField('Funcionario', related_name='servicos', blank=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nome) or 'servico'
            tentativa = base
            i = 1
            while Servico.objects.filter(loja=self.loja, slug=tentativa).exclude(pk=self.pk).exists():
                i += 1
                tentativa = f"{base}-{i}"
            self.slug = tentativa
        super().save(*args, **kwargs)

    @property
    def duracao_timedelta(self):
        from datetime import timedelta
        return timedelta(minutes=int(self.duracao_minutos or 0))

    def __str__(self):
        return f"{self.nome} – {self.loja.nome}"

    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ("nome",)
        unique_together = (("loja", "slug"),)
