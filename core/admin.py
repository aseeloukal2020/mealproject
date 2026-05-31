from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Project, MonitoringReport, Attendance, ProjectProposal,Sector,Program


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'is_approved', 'is_staff', 'date_joined',
    )
    list_filter = ('is_approved', 'role', 'is_staff', 'is_superuser')
    list_editable = ('is_approved', 'role')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    # إضافة حقول role و is_approved لصفحة تعديل المستخدم
    fieldsets = BaseUserAdmin.fieldsets + (
        ('NGO Settings', {
            'fields': ('role', 'is_approved'),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('NGO Settings', {
            'fields': ('role', 'is_approved'),
        }),
    )

    # أكشن سريع للموافقة على عدة مستخدمين دفعة واحدة
    actions = ['approve_users', 'reject_users']

    def approve_users(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} user(s) approved successfully.")
    approve_users.short_description = "✅ Approve selected users"

    def reject_users(self, request, queryset):
        count = queryset.filter(is_superuser=False).delete()[0]
        self.message_user(request, f"{count} user(s) rejected and deleted.")
    reject_users.short_description = "❌ Reject & delete selected users"


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'sector', 'status', 'progress_percentage',
                    'created_by', 'assigned_officer', 'location')
    list_filter = ('sector', 'status')
    search_fields = ('name', 'donor', 'location')
    list_editable = ('assigned_officer',)  # يقدر الأدمن يعيّن الضابط بسرعة


@admin.register(MonitoringReport)
class MonitoringReportAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'officer', 'visit_date',
        'progress_percentage', 'beneficiaries_reached', 'risk_level',
    )
    list_filter = ('risk_level', 'visit_date', 'project__sector')
    search_fields = ('project__name', 'officer__username')
    readonly_fields = ('beneficiaries_reached', 'created_at')

    fields = (
        'project', 'officer', 'visit_date',
        'progress_percentage', 'male', 'female', 'children',
        'beneficiaries_reached', 'risk_level',
        'issues', 'recommendation',
    )

    def save_model(self, request, obj, form, change):
        if not obj.officer_id:
            obj.officer = request.user
        super().save_model(request, obj, form, change)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'date',
        'check_in',
        'check_out',
        'status',
        'is_office_network',
        'ip_address',
    )
    list_filter = ('date', 'status', 'is_office_network')
    search_fields = ('user__username',)
@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)
@admin.register(ProjectProposal)
class ProjectProposalAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'sector',
        'donor',
        'proposed_budget',
        'status',
        'created_by',
        'created_at',
        'project',
    )
    list_filter = ('status', 'sector', 'donor')
    search_fields = ('title', 'donor', 'location')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'sector', 'donor', 'status'),
        }),
        ('Planning', {
            'fields': (
                'proposed_budget',
                'proposed_start_date',
                'proposed_end_date',
                'location',
                'target_beneficiaries',
            ),
        }),
        ('Content', {
            'fields': ('summary', 'proposal_file'),
        }),
        ('Meta', {
            'fields': ('created_by', 'project', 'created_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # لو ما تم تعبئة created_by من قبل، نعيّنه على المستخدم الحالي
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'donor',
        'location',
        'start_date',
        'end_date',
        'created_by',
        'created_at',
    )
    search_fields = ('name', 'donor', 'location')
    list_filter = ('donor', 'location', 'start_date')