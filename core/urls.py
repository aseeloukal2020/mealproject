from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    # path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('pending/', views.pending_approval_view, name='pending_approval'),

    path('', views.dashboard, name='public_dashboard'),
    path('', views.dashboard, name='dashboard'),

    path('projects/', views.projects_list, name='projects'),
    path('projects/add/', views.project_create, name='project_create'),

    path('projects/active/', views.active_projects, name='active_projects'),
    path('projects/delayed/', views.delayed_projects, name='delayed_projects'),
    path('projects/completed/', views.completed_projects, name='completed_projects'),
    path('project/<int:project_id>/', views.project_details, name='project_details'),

    path('reports/', views.reports_list, name='reports_list'),
    path('reports/add/', views.report_create, name='report_create'),
    path('reports/<int:report_id>/download/', views.download_report_file, name='download_report_file'),

    # ========== PROPOSALS ==========
    path('proposals/', views.proposals_list, name='proposals_list'),
    path('proposals/add/', views.proposal_create, name='proposal_create'),
    path(
        'projects/<int:project_id>/proposal/add/',
        views.proposal_create,
        name='proposal_create_for_project'
    ),
    path('proposals/<int:proposal_id>/', views.proposal_detail, name='proposal_detail'),
    path('proposals/<int:proposal_id>/edit/', views.proposal_edit, name='proposal_edit'),
    path(
        'proposals/<int:proposal_id>/create-project/',
        views.proposal_create_project,
        name='proposal_create_project'
    ),
    path('programs/', views.programs_list, name='programs'),
    path('programs/<int:program_id>/', views.program_details, name='program_details'),
]