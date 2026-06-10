from django.db import models

class LabSettings(models.Model):
    session_duration_minutes = models.PositiveIntegerField(
        default=20,
        help_text="Duração máxima da sessão de controlo em minutos."
    )
    entry_timeout_minutes = models.PositiveIntegerField(
        default=1,
        help_text="Tempo para o utilizador confirmar entrada após chegar ao início da fila em minutos."
    )

    class Meta:
        verbose_name = "Configurações do Laboratório"
        verbose_name_plural = "Configurações do Laboratório"

    def __str__(self):
        return f"Timers — Sessão: {self.session_duration_minutes} min | Entrada: {self.entry_timeout_minutes} min"

    @classmethod
    def get_duration(cls):
        obj = cls.objects.first()
        return (obj.session_duration_minutes if obj else 20) * 60  # retorna em segundos
    
    @classmethod
    def get_entry_timeout(cls):
        obj = cls.objects.first()
        return (obj.entry_timeout_minutes if obj else 1) * 60