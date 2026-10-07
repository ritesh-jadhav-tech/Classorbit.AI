import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import { roles } from "./auth/session";
import AdminLayout from "./layouts/AdminLayout";
import Introduction from "./pages/Introduction";
import Login from "./pages/Login";
import PortalPlaceholder from "./pages/PortalPlaceholder";
import Register from "./pages/Register";
import Allocation from "./pages/admin/Allocation";
import Classrooms from "./pages/admin/Classrooms";
import Dashboard from "./pages/admin/Dashboard";
import Departments from "./pages/admin/Departments";
import Events from "./pages/admin/Events";
import Examinations from "./pages/admin/Examinations";
import Faculty from "./pages/admin/Faculty";
import Occupancy from "./pages/admin/Occupancy";
import Profile from "./pages/admin/Profile";
import RoomRequests from "./pages/admin/RoomRequests";
import Settings from "./pages/admin/Settings";
import Subjects from "./pages/admin/Subjects";
import TimeSlots from "./pages/admin/TimeSlots";
import Timetable from "./pages/admin/Timetable";
import Users from "./pages/admin/Users";
import {
  FacultyAvailability,
  FacultyDashboard,
  FacultyProfile,
  FacultyRequests,
  FacultySchedule,
  FacultySettings,
} from "./pages/faculty/FacultyPages";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Introduction />} path="/" />
        <Route element={<Login />} path="/login" />
        <Route element={<Register />} path="/register" />

        <Route element={<ProtectedRoute allowedRoles={[roles.admin]} />}>
          <Route element={<AdminLayout />} path="/admin">
            <Route index element={<Dashboard />} />
            <Route element={<Timetable />} path="timetable" />
            <Route element={<Subjects />} path="subjects" />
            <Route element={<Faculty />} path="faculty" />
            <Route element={<TimeSlots />} path="time-slots" />
            <Route element={<Allocation />} path="allocation" />
            <Route element={<Classrooms />} path="classrooms" />
            <Route element={<RoomRequests />} path="requests" />
            <Route element={<Events />} path="events" />
            <Route element={<Examinations />} path="examinations" />
            <Route element={<Occupancy />} path="occupancy" />
            <Route element={<Departments />} path="departments" />
            <Route element={<Users />} path="users" />
            <Route element={<Settings />} path="settings" />
            <Route element={<Profile />} path="profile" />
          </Route>
        </Route>

        <Route element={<ProtectedRoute allowedRoles={[roles.faculty]} />}>
          <Route element={<AdminLayout />} path="/faculty">
            <Route index element={<FacultyDashboard />} />
            <Route element={<FacultySchedule />} path="schedule" />
            <Route element={<FacultyAvailability />} path="availability" />
            <Route element={<FacultyRequests />} path="requests" />
            <Route element={<FacultySettings />} path="settings" />
            <Route element={<FacultyProfile />} path="profile" />
          </Route>
        </Route>
        <Route element={<PortalPlaceholder portal="Exam Coordinator" />} path="/exam-coordinator/*" />

        <Route element={<Navigate replace to="/admin" />} path="/dashboard" />
        <Route element={<Navigate replace to="/admin/classrooms" />} path="/classrooms" />
        <Route element={<Navigate replace to="/admin/timetable" />} path="/timetable" />
        <Route element={<Navigate replace to="/admin/allocation" />} path="/allocation" />
        <Route element={<Navigate replace to="/admin/occupancy" />} path="/occupancy" />
        <Route element={<Navigate replace to="/admin/settings" />} path="/settings" />
        <Route element={<Navigate replace to="/admin" />} path="*" />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
