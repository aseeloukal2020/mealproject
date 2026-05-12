from django.shortcuts import redirect, render
from .models import Project, ProjectProposal, User
from django.db.models import Avg
from django.db.models import Count
from django.db import models

# الاستيرادات الخاصة بالتقارير
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, FileResponse, Http404
from django.db.models import Sum
from .forms import (
    MonitoringReportForm,
    RegisterForm,
    StyledLoginForm,
    ProjectForm,
    ProjectProposalForm,
)
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .decorators import approved_required
from django.core.paginator import Paginator
def get_user_projects(user):
    """
    الأدمن يشوف كل المشاريع.
    الـ Officer يشوف فقط المشاريع اللي هو مسؤول عنها (assigned_officer أو created_by).
    """
    if user.is_superuser or user.is_staff or getattr(user, 'role', None) == 'ADMIN':
        return Project.objects.all()
    else:
        return Project.objects.filter(
            Q(assigned_officer=user) |
            Q(created_by=user)
        ).distinct()

def dashboard(request):
    # 1) مستخدم داخلي (مسجّل دخول + Approved أو Superuser) → الداشبورد الكامل
    if request.user.is_authenticated and (
        request.user.is_superuser
        or getattr(request.user, 'is_approved', False)
    ):
        user = request.user

        # المشاريع المسموح بها فقط
        projects = get_user_projects(user).prefetch_related('reports')

        total_projects = projects.count()
        active_projects = projects.filter(status='ACTIVE').count()
        delayed_projects = projects.filter(status='DELAYED').count()
        completed_projects = projects.filter(status='COMPLETED').count()

        sectors = projects.values('sector').annotate(total=Count('id'))

        # التقارير فقط للمشاريع المسموح بها
        reports_qs = MonitoringReport.objects.filter(project__in=projects)
        total_reports = reports_qs.count()

        avg_progress = reports_qs.aggregate(
            avg=Avg('progress_percentage')
        )['avg'] or 0

        good, warning, critical = calculate_health(projects)
        total_health = good + warning + critical
        if total_health > 0:
            good_pct = round(good / total_health * 100)
            warning_pct = round(warning / total_health * 100)
            critical_pct = round(critical / total_health * 100)
        else:
            good_pct = warning_pct = critical_pct = 0

        risk_qs = reports_qs.values('risk_level').annotate(total=Count('id'))
        risk_map = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
        for item in risk_qs:
            risk_map[item['risk_level']] = item['total']

        risk_low = risk_map['LOW']
        risk_medium = risk_map['MEDIUM']
        risk_high = risk_map['HIGH']
        total_risk = risk_low + risk_medium + risk_high
        if total_risk > 0:
            risk_low_pct = round(risk_low / total_risk * 100)
            risk_medium_pct = round(risk_medium / total_risk * 100)
            risk_high_pct = round(risk_high / total_risk * 100)
        else:
            risk_low_pct = risk_medium_pct = risk_high_pct = 0

        total_budget = projects.aggregate(sum=Sum('budget'))['sum'] or 0

        total_target_beneficiaries = projects.aggregate(
            sum=Sum('target_beneficiaries')
        )['sum'] or 0

        reached_beneficiaries = 0
        for project in projects:
            latest = project.reports.order_by('-visit_date').first()
            if latest:
                reached_beneficiaries += latest.beneficiaries_reached

        budget_utilization_pct = round(avg_progress or 0, 1)
        if total_budget:
            budget_used = float(total_budget) * (budget_utilization_pct / 100.0)
        else:
            budget_used = 0.0

        open_issues = reports_qs.filter(risk_level='HIGH').count()

        pending_users_count = 0
        if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
            pending_users_count = User.objects.filter(
                is_approved=False,
                is_superuser=False
            ).count()

        context = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'delayed_projects': delayed_projects,
            'completed_projects': completed_projects,

            'sectors': sectors,
            'total_reports': total_reports,
            'avg_progress': round(avg_progress, 1),

            'good': good,
            'warning': warning,
            'critical': critical,
            'good_pct': good_pct,
            'warning_pct': warning_pct,
            'critical_pct': critical_pct,

            'risk_low': risk_low,
            'risk_medium': risk_medium,
            'risk_high': risk_high,
            'risk_low_pct': risk_low_pct,
            'risk_medium_pct': risk_medium_pct,
            'risk_high_pct': risk_high_pct,

            'total_budget': total_budget,
            'budget_used': budget_used,
            'budget_utilization_pct': budget_utilization_pct,
            'reached_beneficiaries': reached_beneficiaries,
            'total_target_beneficiaries': total_target_beneficiaries,

            'open_issues': open_issues,
            'pending_users_count': pending_users_count,
        }

        return render(request, 'dashboard.html', context)

    # 2) زائر (غير مسجّل أو غير Approved) → داشبورد عام
    projects = Project.objects.all().prefetch_related('reports')

    total_projects = projects.count()
    active_projects = projects.filter(status='ACTIVE').count()
    delayed_projects = projects.filter(status='DELAYED').count()
    completed_projects = projects.filter(status='COMPLETED').count()

    sectors = projects.values('sector').annotate(total=Count('id'))

    reports_qs = MonitoringReport.objects.all()
    total_reports = reports_qs.count()

    avg_progress = reports_qs.aggregate(
        avg=Avg('progress_percentage')
    )['avg'] or 0

    good, warning, critical = calculate_health(projects)

    total_budget = projects.aggregate(sum=Sum('budget'))['sum'] or 0
    total_target_beneficiaries = projects.aggregate(
        sum=Sum('target_beneficiaries')
    )['sum'] or 0

    reached_beneficiaries = 0
    for project in projects:
        latest = project.reports.order_by('-visit_date').first()
        if latest:
            reached_beneficiaries += latest.beneficiaries_reached
    budget_utilization_pct = round(avg_progress or 0, 1)
    if total_budget:
        budget_used = float(total_budget) * (budget_utilization_pct / 100.0)
    else:
        budget_used = 0.0

    open_issues = reports_qs.filter(risk_level='HIGH').count()
    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'delayed_projects': delayed_projects,
        'completed_projects': completed_projects,
        'sectors': sectors,
        'total_reports': total_reports,
        'avg_progress': round(avg_progress, 1),
        'good': good,
        'warning': warning,
        'critical': critical,
        'total_budget': total_budget,
        'budget_used': budget_used,
        'budget_utilization_pct': budget_utilization_pct,
        'reached_beneficiaries': reached_beneficiaries,
        'total_target_beneficiaries': total_target_beneficiaries,
        'open_issues': open_issues,
    }

    return render(request, 'public_dashboard.html', context)
@approved_required
def proposals_list(request):
    user = request.user

    # الأدمن يشوف كل البروبوزال، غيره يشوف اللي هو أنشأها
    if user.is_superuser or user.is_staff or getattr(user, 'role', None) == 'ADMIN':
        qs = ProjectProposal.objects.select_related('created_by', 'project')
    else:
        qs = ProjectProposal.objects.filter(
            created_by=user
        ).select_related('created_by', 'project')

    qs = qs.order_by('-created_at')

    # إحصائيات بسيطة لكل حالة (لو حبيتي تستعمليها لاحقاً)
    status_counts = qs.values('status').annotate(total=Count('id'))
    status_map = {'DRAFT': 0, 'SUBMITTED': 0, 'APPROVED': 0, 'REJECTED': 0}
    for item in status_counts:
        status_map[item['status']] = item['total']

    # المناطق (location) للفلتر
    regions = (
        qs.exclude(location__isnull=True)
          .exclude(location__exact='')
          .values_list('location', flat=True)
          .distinct()
          .order_by('location')
    )

    context = {
        'proposals': qs,
        'status_counts': status_map,
        'regions': regions,
    }
    return render(request, 'proposals_list.html', context)
@approved_required
def proposal_create(request):
    user = request.user

    # المشاريع اللي يقدر يربط معها البروبوزال (لو حب)
    allowed_projects = get_user_projects(user)

    if request.method == 'POST':
        form = ProjectProposalForm(request.POST, request.FILES)
        form.fields['project'].queryset = allowed_projects

        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.created_by = user
            proposal.save()
            return redirect('proposals_list')
    else:
        form = ProjectProposalForm()
        form.fields['project'].queryset = allowed_projects

    return render(request, 'proposal_form.html', {'form': form})
@approved_required
def proposal_detail(request, proposal_id):
    proposal = get_object_or_404(ProjectProposal, id=proposal_id)
    user = request.user

    # صلاحية العرض:
    # - أدمن / staff
    # - من أنشأ البروبوزال
    # - أو لو مربوط بمشروع، واليوزر عنده صلاحية على هذا المشروع
    allowed = (
        user.is_superuser or user.is_staff or
        getattr(user, 'role', None) == 'ADMIN' or
        proposal.created_by == user
    )

    if not allowed and proposal.project:
        if (
            user == proposal.project.created_by or
            user == proposal.project.assigned_officer
        ):
            allowed = True

    if not allowed:
        return HttpResponseForbidden("ليس لديك صلاحية لعرض هذا البروبوزال.")

    context = {
        'proposal': proposal,
    }
    return render(request, 'proposal_details.html', context)
@approved_required
def proposal_edit(request, proposal_id):
    proposal = get_object_or_404(ProjectProposal, id=proposal_id)
    user = request.user

    # فقط الأدمن أو من أنشأه
    if not (user.is_superuser or user.is_staff or proposal.created_by == user):
        return HttpResponseForbidden("لا تملك صلاحية تعديل هذا البروبوزال.")

    allowed_projects = get_user_projects(user)

    if request.method == 'POST':
        form = ProjectProposalForm(request.POST, request.FILES, instance=proposal)
        form.fields['project'].queryset = allowed_projects

        if form.is_valid():
            form.save()
            return redirect('proposal_detail', proposal_id=proposal.id)
    else:
        form = ProjectProposalForm(instance=proposal)
        form.fields['project'].queryset = allowed_projects

    context = {
        'form': form,
        'proposal': proposal,
    }
    return render(request, 'proposal_form.html', context)
@approved_required
def proposal_create_project(request, proposal_id):
    proposal = get_object_or_404(ProjectProposal, id=proposal_id)
    user = request.user

    # صلاحيات: خلّيها مبدئياً للأدمن فقط
    if not (user.is_superuser or user.is_staff or getattr(user, 'role', None) == 'ADMIN'):
        return HttpResponseForbidden("You don't have permission to create a project from this proposal.")

    # لو البروبوزال مرتبط أصلاً بمشروع، نرجع له مباشرة
    if proposal.project:
        return redirect('project_details', project_id=proposal.project.id)

    if request.method == 'POST':
        # إنشاء المشروع من بيانات البروبوزال
        project = Project.objects.create(
            name=proposal.title,
            sector=proposal.sector,
            donor=proposal.donor,
            budget=proposal.proposed_budget,
            start_date=proposal.proposed_start_date,
            end_date=proposal.proposed_end_date,
            location=proposal.location,
            target_beneficiaries=proposal.target_beneficiaries,
            status='ACTIVE',                    # افتراضي
            created_by=user,                    # من أنشأ المشروع
            assigned_officer=proposal.created_by  # المنسّق الافتراضي: صاحب البروبوزال
        )

        # ربط البروبوزال بالمشروع
        proposal.project = project
        if proposal.status == 'SUBMITTED':
            proposal.status = 'APPROVED'
        proposal.save()

        return redirect('project_details', project_id=project.id)

    # لو GET نرجع لصفحة البروبوزال (ما في داعي لعرض صفحة خاصة)
    return redirect('proposal_detail', proposal_id=proposal.id)
def calculate_health(projects):
    good = 0
    warning = 0
    critical = 0

    for project in projects:
        health = project.get_health_status()

        if health == "Good":
            good += 1
        elif health == "Warning":
            warning += 1
        elif health == "Critical":
            critical += 1

    return good, warning, critical
def active_projects(request):

    projects = Project.objects.filter(status='ACTIVE')
    good, warning, critical = calculate_health(projects)
    return render(request, 'projects.html', 
    {
        'projects': projects,
        'good': good,
        'warning': warning,
        'critical': critical,
        })


def delayed_projects(request):

    projects = Project.objects.filter(status='DELAYED')
    good, warning, critical = calculate_health(projects)
    return render(request, 'projects.html', {
        'projects': projects,
        'good': good,
        'warning': warning,
        'critical': critical,
        })


def completed_projects(request):

    projects = Project.objects.filter(status='COMPLETED')
    good, warning, critical = calculate_health(projects)


    return render(request, 'projects.html', {
        'projects': projects,
        'good': good,
        'warning': warning,
        'critical': critical,
        })




from django.shortcuts import render
from .models import User, Project, MonitoringReport, Attendance
@approved_required
def projects_list(request):
    user = request.user

    # المشاريع المسموح بها فقط
    projects =( get_user_projects(user)
    .prefetch_related('reports')
    .order_by('-created_at')
    )
    # حساب health + آخر تقرير
    for p in projects:
        p.health = p.get_health_status()
        latest = p.reports.order_by('-visit_date').first()
        if latest:
            p.latest_risk = latest.risk_level
            p.latest_beneficiaries = latest.beneficiaries_reached
        else:
            p.latest_risk = None
            p.latest_beneficiaries = 0

    good = warning = critical = 0
    for p in projects:
        if p.health == "Good":
            good += 1
        elif p.health == "Warning":
            warning += 1
        elif p.health == "Critical":
            critical += 1

    # المناطق الفريدة فقط من المشاريع المسموح بها
    regions = (
        Project.objects.filter(id__in=[p.id for p in projects])
        .exclude(location__isnull=True)
        .exclude(location__exact='')
        .values_list('location', flat=True)
        .distinct()
        .order_by('location')
    )
    project_form = ProjectForm()
    context = {
        'projects': projects,
        'good': good,
        'warning': warning,
        'critical': critical,
        'regions': regions,
        'project_form': project_form,
    }
    return render(request, 'projects.html', context)
@approved_required
def project_create(request):
    user = request.user

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = user   # من أنشأ المشروع

            # لو لم يتم اختيار assigned_officer، نخليه المستخدم الحالي
            if not project.assigned_officer:
                project.assigned_officer = user

            project.save()
            return redirect('projects')   # يرجع لقائمة المشاريع
    else:
        form = ProjectForm()

    # في الوضع العادي لن نستخدم GET هنا (لأننا نقوم بعرض المودال داخل صفحة المشاريع)
    # لكن نتركه احتياطاً
    return render(request, 'project_form.html', {'form': form})
@approved_required
def project_details(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    user = request.user

    # فحص صلاحية الوصول للمشروع
    if not (
        user.is_superuser or user.is_staff or
        getattr(user, 'role', None) == 'ADMIN' or
        user == project.created_by or
        user == project.assigned_officer
    ):
        return HttpResponseForbidden("You don't have permission to view this project.")

    reports = MonitoringReport.objects.filter(
        project=project
    ).order_by('-visit_date')

    latest_reports = reports[:7]   # للجدول فقط

    context = {
        'project': project,
        'reports': reports,         # كل التقارير للـ Charts
        'latest_reports': latest_reports,
    }
    return render(request, 'project_details.html', context)
# لعرض التقارير
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import MonitoringReport


from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import MonitoringReport


@approved_required
def reports_list(request):
    user = request.user

    # صلاحيات: الأدمن يشوف كل التقارير، الباقي بس تقاريرهم
    if user.is_superuser or user.is_staff or getattr(user, 'role', None) == 'ADMIN':
        qs = MonitoringReport.objects.select_related('project', 'officer')
    else:
        qs = MonitoringReport.objects.filter(
            Q(project__created_by=user) |
            Q(project__assigned_officer=user) |
            Q(officer=user)
        ).select_related('project', 'officer').distinct()

    # ترتيب من الأحدث للأقدم
    qs = qs.order_by('-visit_date')

    # قوائم الفلاتر بدون تكرار
    projects_list_filter = (
        qs.values_list('project__name', flat=True)
        .distinct()
        .order_by('project__name')
    )

    officers_list_filter = (
        qs.values_list('officer__username', flat=True)
        .distinct()
        .order_by('officer__username')
    )

    # Pagination: 10 تقارير في كل صفحة
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_reports': qs.count(),
        'projects_filter': projects_list_filter,
        'officers_filter': officers_list_filter,
    }
    return render(request, 'reports_list.html', context)
# لاضافة تقرير جديد
@approved_required
def report_create(request):
    user = request.user

    # نحدّد أي المشاريع يقدر يختارها
    if user.role == 'ADMIN':
        allowed_projects = Project.objects.all()
    else:
        allowed_projects = Project.objects.filter(
            Q(created_by=user) |
            Q(assigned_officer=user)
        ).distinct()

    if request.method == 'POST':
        form = MonitoringReportForm(request.POST, request.FILES)
        # حصر المشاريع في الفورم بالمسموح
        form.fields['project'].queryset = allowed_projects

        if form.is_valid():
            report = form.save(commit=False)
            report.officer = user
            report.save()
            return redirect('reports_list')
    else:
        form = MonitoringReportForm()
        form.fields['project'].queryset = allowed_projects

    return render(request, 'report_form.html', {'form': form})
# لامكانية تنزيل التقارير
@approved_required
def download_report_file(request, report_id):
    report = get_object_or_404(MonitoringReport, id=report_id)
    user = request.user

    # نفس منطق الخصوصية
    if not (
        user.role == 'ADMIN' or
        user == report.project.created_by or
        user == report.project.assigned_officer or
        user == report.officer
    ):
        return HttpResponseForbidden("ليس لديك صلاحية لتنزيل هذا التقرير.")

    if not report.report_file:
        raise Http404("لا يوجد ملف مرفق لهذا التقرير.")

    return FileResponse(
        report.report_file.open('rb'),
        as_attachment=True,
        filename=report.report_file.name.split('/')[-1],
    )
# ========== AUTH VIEWS ==========

def register_view(request):
    # لو مسجل دخول أصلاً يروح للداشبورد
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('pending_approval')
    else:
        form = RegisterForm()

    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_approved or request.user.is_superuser:
            return redirect('dashboard')
        else:
            return redirect('pending_approval')

    if request.method == 'POST':
        form = StyledLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            register_attendance_login(request, user) 
            # لو المستخدم مش معتمد، يروح لصفحة الانتظار
            if not user.is_approved and not user.is_superuser:
                return redirect('pending_approval')

            return redirect('dashboard')
    else:
        form = StyledLoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    user = request.user
    if user.is_authenticated:
        # تسجيل وقت الخروج في الحضور
        register_attendance_logout(request, user, manual=True)

    logout(request)
    return redirect('login')


@login_required
def pending_approval_view(request):
    # لو المستخدم معتمد أصلاً، يروح للداشبورد
    if request.user.is_approved or request.user.is_superuser:
        return redirect('dashboard')

    return render(request, 'auth/pending_approval.html')

import ipaddress

def get_client_ip(request):
    """
    إحضار عنوان الـ IP الحقيقي (مع مراعاة X-Forwarded-For لو فيه Proxy).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # أول IP في السلسلة
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_office_ip(ip):
    """
    حالياً: نعتبر أي IP من الشبكات الخاصة Private كـ "Office" (10.x, 192.168.x, 172.16-31.x)
    هذا تقريب تقريبي، ونقدر نعدّله لاحقاً لو حبيتي فقط شبكة معيّنة.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private

from django.utils import timezone


from .models import User, Project, MonitoringReport, Attendance
import ipaddress


def register_attendance_login(request, user):
    """
    تُستدعى عند تسجيل الدخول الناجح.
    إمّا تنشئ سجل حضور جديد لليوم، أو تحدّث السجل الموجود.
    وتخزن رقم هذا السجل في session.
    """
    if not user.is_authenticated:
        return

    today = timezone.localdate()
    now = timezone.now()
    ip = get_client_ip(request)
    office = is_office_ip(ip)

    attendance, created = Attendance.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            'check_in': now,
            'last_activity': now,
            'ip_address': ip,
            'is_office_network': office,
            'status': 'PRESENT',
        }
    )

    if not created:
        attendance.last_activity = now
        attendance.status = 'PRESENT'
        if ip and not attendance.ip_address:
            attendance.ip_address = ip
        attendance.save()

    # الخدعة هنا: نخزّن رقم السجل في الـ session
    request.session['attendance_id'] = attendance.id

from django.core.exceptions import ObjectDoesNotExist

def register_attendance_logout(request, user, manual=True):
    """
    تُستدعى عند تسجيل الخروج.
    نحدِّث check_out للسجل المخزَّن في الـ session إن وجد،
    وإلا نحاول إيجاد آخر سجل لهذا اليوم.
    """
    if not user.is_authenticated:
        return

    now = timezone.now()
    today = timezone.localdate()

    attendance = None

    # 1) المحاولة الأولى: من الـ session
    attendance_id = request.session.get('attendance_id')
    if attendance_id:
        try:
            attendance = Attendance.objects.get(id=attendance_id, user=user)
        except Attendance.DoesNotExist:
            attendance = None

    # 2) لو ما لقيناه في الـ session، نرجع لطريقة user+date
    if attendance is None:
        try:
            attendance = Attendance.objects.filter(user=user, date=today).order_by('-check_in').first()
        except ObjectDoesNotExist:
            attendance = None

    if attendance is None:
        # ما في حضور لهذا اليوم (ما سجّل دخول أصلاً)
        return

    # لو ما تم تسجيل خروج من قبل أو هذا الخروج أحدث وقتاً
    if attendance.check_out is None or now > attendance.check_out:
        attendance.check_out = now
        attendance.last_activity = now
        attendance.status = 'LEFT_MANUAL' if manual else 'LEFT_TIMEOUT'
        attendance.save()

    # نحذف القيمة من الـ session عشان ما تتداخل مع اليوم التالي
    if 'attendance_id' in request.session:
        del request.session['attendance_id']