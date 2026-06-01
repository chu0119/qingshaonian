import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import ProtectedRoute from './ProtectedRoute';
import MainLayout from '../components/layout/MainLayout';
import StudentLayout from '../components/layout/StudentLayout';
import LoginPage from '../pages/LoginPage';
import ForceChangePassword from '../pages/ForceChangePassword';
import ForbiddenPage from '../pages/403';
import NotFoundPage from '../pages/404';

// 学校管理员页面
import SchoolDashboard from '../pages/school-admin/Dashboard';
import ClassManagement from '../pages/school-admin/ClassManagement';
import StudentManagement from '../pages/school-admin/StudentManagement';
import TeacherManagement from '../pages/school-admin/TeacherManagement';
import QuestionnaireLibrary from '../pages/school-admin/QuestionnaireLibrary';
import QuestionnaireEditor from '../pages/school-admin/QuestionnaireEditor';
import TaskManagement from '../pages/school-admin/TaskManagement';
import RiskWarning from '../pages/school-admin/RiskWarning';
import RiskDetail from '../pages/school-admin/RiskDetail';
import InterventionRecords from '../pages/school-admin/InterventionRecords';
import DataReports from '../pages/school-admin/DataReports';
import DataScreen from '../pages/school-admin/DataScreen';
import SystemSettings from '../pages/school-admin/SystemSettings';
import SchoolAuditLogs from '../pages/school-admin/AuditLogs';
import StudentProfile360 from '../pages/school-admin/StudentProfile';

// 平台端学生档案包装组件
function PlatformStudentProfile() {
  return <StudentProfile360 platformMode />;
}

// 教师页面
import TeacherDashboard from '../pages/teacher/TeacherDashboard';
import MyClasses from '../pages/teacher/MyClasses';
import MyQuestionnaires from '../pages/teacher/MyQuestionnaires';
import TeacherTasks from '../pages/teacher/TeacherTasks';
import CompletionStatus from '../pages/teacher/CompletionStatus';
import RiskStudents from '../pages/teacher/RiskStudents';
import TeacherInterventions from '../pages/teacher/TeacherInterventions';
import ClassReport from '../pages/teacher/ClassReport';

// 学生页面
import StudentHome from '../pages/student/StudentHome';
import PendingQuestionnaires from '../pages/student/PendingQuestionnaires';
import AnswerPage from '../pages/student/AnswerPage';
import CompletedQuestionnaires from '../pages/student/CompletedQuestionnaires';
import StudentProfile from '../pages/student/Profile';
import StudentHealthTips from '../pages/student/HealthTips';

// 平台管理员页面
import SchoolManagement from '../pages/platform/SchoolManagement';
import PlatformDashboard from '../pages/platform/Dashboard';
import PlatformSettings from '../pages/platform/Settings';
import PlatformScreen from '../pages/platform/Screen';
import PlatformRiskCenter from '../pages/platform/RiskCenter';
import PlatformKeyStudents from '../pages/platform/KeyStudents';
import PlatformTaskSupervision from '../pages/platform/TaskSupervision';
import PlatformInterventionSupervision from '../pages/platform/InterventionSupervision';
import PlatformAuditLogs from '../pages/platform/AuditLogs';
import PlatformSmsCenter from '../pages/platform/Notifications';
import PlatformAIAnalysis from '../pages/platform/AIAnalysis';
import PlatformStudentManagement from '../pages/platform/StudentManagement';
import PlatformQuestionnaireManagement from '../pages/platform/QuestionnaireManagement';
import PlatformStudentProfilePage from '../pages/platform/StudentProfilePage';

function RootRedirect() {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" replace />;

  const roleRedirectMap: Record<string, string> = {
    school_admin: '/school-admin/dashboard',
    teacher: '/teacher/dashboard',
    counselor: '/counselor/dashboard',
    student: '/student/home',
    platform_admin: '/platform/dashboard',
  };

  return <Navigate to={roleRedirectMap[user.role] || '/login'} replace />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/change-password" element={
        <ProtectedRoute>
          <ForceChangePassword />
        </ProtectedRoute>
      } />
      <Route path="/403" element={<ForbiddenPage />} />

      {/* 独立大屏路由 */}
      <Route
        path="/school-admin/screen"
        element={
          <ProtectedRoute roles={['school_admin']}>
            <DataScreen />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/screen"
        element={
          <ProtectedRoute roles={['platform_admin']}>
            <PlatformScreen />
          </ProtectedRoute>
        }
      />

      {/* 学校管理员路由 */}
      <Route
        path="/school-admin"
        element={
          <ProtectedRoute roles={['school_admin']}>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<SchoolDashboard />} />
        <Route path="classes" element={<ClassManagement />} />
        <Route path="students" element={<StudentManagement />} />
        <Route path="teachers" element={<TeacherManagement />} />
        <Route path="questionnaires" element={<QuestionnaireLibrary />} />
        <Route path="questionnaires/new" element={<QuestionnaireEditor />} />
        <Route path="questionnaires/:id/edit" element={<QuestionnaireEditor />} />
        <Route path="tasks" element={<TaskManagement />} />
        <Route path="risks" element={<RiskWarning />} />
        <Route path="risks/:id" element={<RiskDetail />} />
        <Route path="interventions" element={<InterventionRecords />} />
        <Route path="reports" element={<DataReports />} />
        <Route path="audit-logs" element={<SchoolAuditLogs />} />
        <Route path="students/:id" element={<StudentProfile360 />} />
        <Route path="settings" element={<SystemSettings />} />
      </Route>

      {/* 教师路由 */}
      <Route
        path="/teacher"
        element={
          <ProtectedRoute roles={['teacher']}>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<TeacherDashboard />} />
        <Route path="classes" element={<MyClasses />} />
        <Route path="questionnaires" element={<MyQuestionnaires />} />
        <Route path="questionnaires/new" element={<QuestionnaireEditor />} />
        <Route path="questionnaires/:id/edit" element={<QuestionnaireEditor />} />
        <Route path="tasks" element={<TeacherTasks />} />
        <Route path="completion" element={<CompletionStatus />} />
        <Route path="risks" element={<RiskStudents />} />
        <Route path="interventions" element={<TeacherInterventions />} />
        <Route path="reports" element={<ClassReport />} />
      </Route>

      {/* 平台管理员路由 */}
      <Route
        path="/platform"
        element={
          <ProtectedRoute roles={['platform_admin']}>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<PlatformDashboard />} />
        <Route path="schools" element={<SchoolManagement />} />
        <Route path="risks" element={<PlatformRiskCenter />} />
        <Route path="students" element={<PlatformStudentManagement />} />
        <Route path="students/:id" element={<PlatformStudentProfile />} />
        <Route path="student-profile" element={<PlatformStudentProfilePage />} />
        <Route path="questionnaires" element={<PlatformQuestionnaireManagement />} />
        <Route path="questionnaires/new" element={<QuestionnaireEditor />} />
        <Route path="questionnaires/:id/edit" element={<QuestionnaireEditor />} />
        <Route path="key-students" element={<PlatformKeyStudents />} />
        <Route path="tasks" element={<PlatformTaskSupervision />} />
        <Route path="interventions" element={<PlatformInterventionSupervision />} />
        <Route path="ai-analysis" element={<PlatformAIAnalysis />} />
        <Route path="notifications" element={<PlatformSmsCenter />} />
        <Route path="audit-logs" element={<PlatformAuditLogs />} />
        <Route path="settings" element={<PlatformSettings />} />
      </Route>

      {/* 心理老师路由 */}
      <Route
        path="/counselor"
        element={
          <ProtectedRoute roles={['counselor']}>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<TeacherDashboard />} />
        <Route path="classes" element={<MyClasses />} />
        <Route path="students" element={<StudentManagement />} />
        <Route path="risks" element={<RiskStudents />} />
        <Route path="interventions" element={<TeacherInterventions />} />
        <Route path="tasks" element={<TeacherTasks />} />
        <Route path="completion" element={<CompletionStatus />} />
        <Route path="reports" element={<ClassReport />} />
      </Route>

      {/* 学生路由 */}
      <Route
        path="/student"
        element={
          <ProtectedRoute roles={['student']}>
            <StudentLayout />
          </ProtectedRoute>
        }
      >
        <Route path="home" element={<StudentHome />} />
        <Route path="pending" element={<PendingQuestionnaires />} />
        <Route path="answer/:answerSheetId" element={<AnswerPage />} />
        <Route path="completed" element={<CompletedQuestionnaires />} />
        <Route path="health-tips" element={<StudentHealthTips />} />
        <Route path="profile" element={<StudentProfile />} />
      </Route>

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
