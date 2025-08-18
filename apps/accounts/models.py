from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_owner", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa is_superuser=True")
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None  # não usar username
    email = models.EmailField(unique=True)

    # flags de perfil
    is_owner = models.BooleanField(default=False)
    is_client = models.BooleanField(default=False)

    # dados do cliente (agendamento)
    phone_regex = RegexValidator(r"^\+?\d{10,15}$", "Informe telefone no formato internacional, ex.: +5585...")
    phone = models.CharField(max_length=17, blank=True, null=True, validators=[phone_regex])
    full_name = models.CharField(max_length=120, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        role = "Owner" if self.is_owner else ("Cliente" if self.is_client else "Usuário")
        return f"{self.email or self.full_name} ({role})"

class Plan(models.TextChoices):
    FREE = "free", "Free (7 dias)"
    PREMIUM = "premium", "Premium (30 dias)"
    PLATINUM = "platinum", "Platinum (1 ano)"

class Subscription(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    def is_active(self) -> bool:
        return timezone.now() <= self.end_date

    def __str__(self):
        return f"{self.owner.email} – {self.plan} até {self.end_date:%d/%m/%Y}"

class ClientOTP(models.Model):
    """Códigos de verificação para login via telefone (cliente)."""
    phone = models.CharField(max_length=17)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def __str__(self):
        return f"OTP {self.phone} expira {self.expires_at:%H:%M:%S}"