from django.utils import timezone

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('OFFICER', 'Monitoring Officer'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='OFFICER')
    is_approved = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)  

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
class Sector(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
class Program(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    donor = models.CharField(max_length=200, blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    location = models.CharField(max_length=200, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
class Project(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('DELAYED', 'Delayed'),
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects'
    )
    name = models.CharField(max_length=200)
    sector = models.ForeignKey(
    Sector,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='projects'
)
    donor = models.CharField(max_length=200)
    budget = models.DecimalField(max_digits=12, decimal_places=2)

    start_date = models.DateField()
    end_date = models.DateField()

    location = models.CharField(max_length=200)
    target_beneficiaries = models.IntegerField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_projects'
    )

    assigned_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_projects'
    )

    created_at = models.DateTimeField(default=timezone.now)
    progress_percentage = models.IntegerField(default=0)
    def get_health_status(self): #نتيجة تحليل كل مشروع حسب متغيراته 
     reports = self.reports.all()

     if not reports:
        return "No Data"

     latest = reports.order_by('-visit_date').first() # احضار اخر تقرير او اخر حاله للمشروع 
     
     progress = latest.progress_percentage
     risk = latest.risk_level
     beneficiaries = latest.beneficiaries_reached

     if risk == "HIGH" or progress < 40:
        return "Critical"
     elif progress < 70 or beneficiaries < 50:
        return "Warning"
     else:
        return "Good"
    def __str__(self):
        return self.name
class ProjectProposal(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted to donor'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    title = models.CharField(max_length=200)
    sector = models.ForeignKey(
    Sector,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='proposals'
)
    donor = models.CharField(max_length=200)

    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2)
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()

    location = models.CharField(max_length=200)
    target_beneficiaries = models.IntegerField()

    summary = models.TextField(
        null=True,
        blank=True,
        help_text="ملخص للبروبوزال (الأهداف، الأنشطة الرئيسية، المؤشرات...)"
    )

    proposal_file = models.FileField(
        upload_to='proposals/',
        null=True,
        blank=True,
        help_text="ارفع ملف البروبوزال (PDF, Word, ...)"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='proposals'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # بعد ما يتحول إلى مشروع حقيقي نربطه هنا
    project = models.OneToOneField(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposal'
    )

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
class MonitoringReport(models.Model):

    RISK_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    officer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')

    visit_date = models.DateField()
    progress_percentage = models.IntegerField()
    #بشكل عام المجموع الكلي Aggregated
    beneficiaries_reached = models.IntegerField(default=0) # يقبل قيمة افتراضية يعني مش اجباري
    #للتفصيل datailed
    male = models.IntegerField(default=0)
    female = models.IntegerField(default=0)
    children = models.IntegerField(default=0)
   

    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES)

    issues = models.TextField()
    recommendation = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)
    def __str__(self):
        return f"{self.project.name} - {self.visit_date}"
# لحتى ما يصير mismatch ويحسب النظام لحاله التوتال 
    def save(self, *args, **kwargs):
        self.beneficiaries_reached = self.male + self.female + self.children
        super().save(*args, **kwargs)

        reports = self.project.reports.all()
        total = sum(report.progress_percentage for report in reports)
        average = total // reports.count()

        self.project.progress_percentage = average
        self.project.save()
from django.utils import timezone
import ipaddress  # سنحتاجه لاحقاً لتقييم نوع الـ IP


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('LEFT_MANUAL', 'Left (manual)'),
        ('LEFT_TIMEOUT', 'Left (timeout)'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendances'
    )

    date = models.DateField()  # تاريخ اليوم
    check_in = models.DateTimeField()  # أول وقت دخول
    check_out = models.DateTimeField(null=True, blank=True)  # وقت الخروج (اختياري)
    last_activity = models.DateTimeField(null=True, blank=True)  # آخر نشاط

    ip_address = models.GenericIPAddressField(null=True, blank=True)  # IP أول ما دخل
    is_office_network = models.BooleanField(default=False)  # لاحقاً نفرّق بين Office/Remote

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PRESENT'
    )

    class Meta:
        ordering = ['-date', '-check_in']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='unique_attendance_per_user_per_day'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    def duration(self):
        """
        مدة التواجد في هذا اليوم (من check_in إلى check_out أو الآن لو لسا موجود)
        """
        end = self.check_out or timezone.now()
        return end - self.check_in