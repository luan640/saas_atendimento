from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, RegexValidator
from django.utils.text import slugify

User = settings.AUTH_USER_MODEL

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
