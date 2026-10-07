import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { clearSession, getSession } from "../auth/session";
import { classOrbitApi } from "../services/classOrbitApi";

const icons = {
  overview: "M4 5.5A1.5 1.5 0 0 1 5.5 4h4A1.5 1.5 0 0 1 11 5.5v4A1.5 1.5 0 0 1 9.5 11h-4A1.5 1.5 0 0 1 4 9.5v-4Zm9 0A1.5 1.5 0 0 1 14.5 4h4A1.5 1.5 0 0 1 20 5.5v4a1.5 1.5 0 0 1-1.5 1.5h-4A1.5 1.5 0 0 1 13 9.5v-4ZM4 14.5A1.5 1.5 0 0 1 5.5 13h4a1.5 1.5 0 0 1 1.5 1.5v4A1.5 1.5 0 0 1 9.5 20h-4A1.5 1.5 0 0 1 4 18.5v-4Zm9 0a1.5 1.5 0 0 1 1.5-1.5h4a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 1-1.5 1.5h-4a1.5 1.5 0 0 1-1.5-1.5v-4Z",
  timetable: "M7 3v3M17 3v3M4 9h16M6 5h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm2 8h3M13 13h3M8 16h3",
  allocation: "M6 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm12 14a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM8.5 5H14a4 4 0 0 1 4 4v7M15 13l3 3 3-3M15.5 19H10a4 4 0 0 1-4-4V8",
  classrooms: "M4 20h16M6 20V5a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v15M9 8h2M13 8h2M9 12h2M13 12h2M10 20v-4h4v4",
  requests: "M4 6h16v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Zm0 0 4 7h8l4-7M9 4h6",
  events: "M7 3v3M17 3v3M4 9h16M6 5h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm5 11 2 2 4-5",
  exams: "M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm7 0v5h5M8 13h8M8 17h6",
  occupancy: "M3 7h4l2-3h6l2 3h4v12H3V7Zm9 9a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-2.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
  departments: "M4 7 12 3l8 4-8 4-8-4Zm0 5 8 4 8-4M4 17l8 4 8-4",
  users: "M16 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM21 20v-2a4 4 0 0 0-3-3.87M15.5 4.13a3 3 0 0 1 0 5.74",
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 8.92 4a1.65 1.65 0 0 0 1-1.51V2a2 2 0 1 1 4 0v.09A1.65 1.65 0 0 0 15 3.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.14.45.52.82 1 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z",
  profile: "M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z",
  logout: "M10 17l5-5-5-5M15 12H3M21 3v18h-7",
  menu: "M4 7h16M4 12h16M4 17h16",
  collapse: "M15 18l-6-6 6-6",
  expand: "M9 18l6-6-6-6",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4",
  findRoom: "M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Zm-8 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
};

function Icon({ name }) {
  return (
    <svg aria-hidden="true" className="app-icon" fill="none" viewBox="0 0 24 24">
      <path d={icons[name]} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

const adminNavGroups = [
  {
    label: "Academic",
    items: [
      { to: "/admin/timetable", label: "Timetable", icon: "timetable" },
      { to: "/admin/subjects", label: "Subjects", icon: "departments" },
      { to: "/admin/faculty", label: "Faculty", icon: "users" },
      { to: "/admin/time-slots", label: "Time Slots", icon: "timetable" },
      { to: "/admin/allocation", label: "Classroom Allocation", icon: "allocation" },
      { to: "/admin/classrooms", label: "Classrooms", icon: "classrooms" },
    ],
  },
  {
    label: "Requests",
    items: [
      { to: "/admin/requests", label: "Room Requests", icon: "requests" },
      { to: "/admin/events", label: "Events", icon: "events" },
      { to: "/admin/examinations", label: "Examinations", icon: "exams" },
    ],
  },
  {
    label: "Intelligence",
    items: [{ to: "/admin/occupancy", label: "Occupancy", icon: "occupancy" }],
  },
  {
    label: "Management",
    items: [
      { to: "/admin/departments", label: "Departments", icon: "departments" },
      { to: "/admin/users", label: "Users", icon: "users" },
    ],
  },
];

const facultyNavGroups = [
  {
    label: "Teaching",
    items: [
      { to: "/faculty/schedule", label: "My Schedule", icon: "timetable" },
      { to: "/faculty/availability", label: "Find a Room", icon: "findRoom" },
      { to: "/faculty/requests", label: "My Requests", icon: "requests" },
    ],
  },
];

const titles = {
  "/admin": "Overview",
  "/admin/timetable": "Timetable",
  "/admin/subjects": "Subjects",
  "/admin/faculty": "Faculty",
  "/admin/time-slots": "Time Slots",
  "/admin/allocation": "Classroom Allocation",
  "/admin/classrooms": "Classrooms",
  "/admin/requests": "Room Requests",
  "/admin/events": "Events",
  "/admin/examinations": "Examinations",
  "/admin/occupancy": "Occupancy",
  "/admin/departments": "Departments",
  "/admin/users": "Users",
  "/admin/settings": "Settings",
  "/admin/profile": "Profile",
  "/faculty": "Today",
  "/faculty/schedule": "My Schedule",
  "/faculty/availability": "Find a Room",
  "/faculty/requests": "My Requests",
  "/faculty/settings": "Settings",
  "/faculty/profile": "Profile",
};

function SidebarContent({ closeMenu, isCollapsed, toggleCollapse, portal }) {
  const isFaculty = portal === "faculty";
  const rootPath = isFaculty ? "/faculty" : "/admin";
  const navGroups = isFaculty ? facultyNavGroups : adminNavGroups;
  const linkClass = ({ isActive }) => `admin-nav-link ${isActive ? "active" : ""}`;
  const handleNavClick = () => closeMenu();

  return (
    <>
      <div className="sidebar-brand-row">
        <NavLink className="brand-lockup" onClick={handleNavClick} to={rootPath}>
          <img alt="ClassOrbit" className="brand-logo" src="/classorbit-logo.png" />
          <span className="brand-copy">
            <strong>ClassOrbit</strong>
            <small>Smart Rooms. Smarter Allocation.</small>
          </span>
        </NavLink>
        <button
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="icon-button sidebar-toggle"
          onClick={toggleCollapse}
          type="button"
        >
          <Icon name={isCollapsed ? "expand" : "collapse"} />
        </button>
      </div>

      <nav className="admin-nav" aria-label={`${portal} navigation`}>
        <NavLink className={linkClass} end onClick={handleNavClick} to={rootPath}>
          <span className="nav-glyph">
            <Icon name="overview" />
          </span>
          <span className="nav-label">{isFaculty ? "Today" : "Overview"}</span>
        </NavLink>

        {navGroups.map((group) => (
          <div className="nav-group" key={group.label}>
            <p>{group.label}</p>
            {group.items.map((item) => (
              <NavLink className={linkClass} key={item.to} onClick={handleNavClick} to={item.to}>
                <span className="nav-glyph">
                  <Icon name={item.icon} />
                </span>
                <span className="nav-label">{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer compact-footer">
        <NavLink aria-label="Settings" title="Settings" className={linkClass} onClick={handleNavClick} to={`${rootPath}/settings`}>
          <span className="nav-glyph">
            <Icon name="settings" />
          </span>
        </NavLink>
        <NavLink aria-label="Profile" title="Profile" className={linkClass} onClick={handleNavClick} to={`${rootPath}/profile`}>
          <span className="nav-glyph">
            <Icon name="profile" />
          </span>
        </NavLink>
        <NavLink aria-label="Logout" title="Logout" className="admin-nav-link" onClick={clearSession} to="/login">
          <span className="nav-glyph">
            <Icon name="logout" />
          </span>
        </NavLink>
      </div>
    </>
  );
}

function AdminLayout() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const { pathname } = useLocation();
  const session = getSession();
  const portal = pathname.startsWith("/faculty") ? "faculty" : "admin";
  const hasAccessToken = Boolean(session?.accessToken);
  const title = titles[pathname] || (portal === "faculty" ? "Faculty" : "Admin");
  const [notifications, setNotifications] = useState([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [lastSeen, setLastSeen] = useState(() => window.localStorage.getItem("classorbit-notifications-seen") || "");

  useEffect(() => {
    if (portal !== "admin" || !hasAccessToken) return undefined;
    const loadNotifications = () => classOrbitApi.getNotifications().then(setNotifications).catch(() => setNotifications([]));
    loadNotifications();
    window.addEventListener("classorbit:imports-updated", loadNotifications);
    return () => window.removeEventListener("classorbit:imports-updated", loadNotifications);
  }, [hasAccessToken, portal]);

  const unreadCount = notifications.filter((item) => !lastSeen || item.createdAt > lastSeen).length;
  const toggleNotifications = () => {
    const nextOpen = !notificationsOpen;
    setNotificationsOpen(nextOpen);
    if (nextOpen) {
      const seenAt = new Date().toISOString();
      window.localStorage.setItem("classorbit-notifications-seen", seenAt);
      setLastSeen(seenAt);
    }
  };

  return (
    <div className={isSidebarCollapsed ? "admin-shell sidebar-collapsed" : "admin-shell"}>
      <aside className="admin-sidebar">
        <SidebarContent
          closeMenu={() => setIsMenuOpen(false)}
          isCollapsed={isSidebarCollapsed}
          portal={portal}
          toggleCollapse={() => setIsSidebarCollapsed((value) => !value)}
        />
      </aside>

      {isMenuOpen ? (
        <div className="mobile-nav-backdrop" onClick={() => setIsMenuOpen(false)}>
          <aside className="mobile-nav-panel" onClick={(event) => event.stopPropagation()}>
            <SidebarContent
              closeMenu={() => setIsMenuOpen(false)}
              isCollapsed={false}
              portal={portal}
              toggleCollapse={() => setIsMenuOpen(false)}
            />
          </aside>
        </div>
      ) : null}

      <div className="admin-main">
        <header className="admin-topbar">
          <button
            aria-label="Open navigation"
            className="mobile-menu-button"
            onClick={() => setIsMenuOpen(true)}
            type="button"
          >
            <Icon name="menu" />
          </button>

          <div>
            <span>{portal === "faculty" ? "Faculty Portal" : "Admin Portal"}</span>
            <h1>{title}</h1>
          </div>

          <div className="topbar-user">
            <div className="notification-wrap">
              <button aria-label="Notifications" className="icon-button notification-button" onClick={toggleNotifications} type="button">
                <Icon name="bell" />
                {unreadCount ? <span className="notification-count">{Math.min(unreadCount, 9)}</span> : null}
              </button>
              {notificationsOpen ? (
                <div className="notification-panel">
                  <div className="notification-heading">
                    <strong>Notifications</strong>
                    <span>{notifications.length} recent</span>
                  </div>
                  <div className="notification-list">
                    {notifications.map((item) => (
                      <div className={`notification-item ${item.status === "FAILED" ? "failed" : ""}`} key={item.id}>
                        <strong>{item.title}</strong>
                        <p>{item.message}</p>
                        <time>{new Date(item.createdAt).toLocaleString()}</time>
                      </div>
                    ))}
                    {!notifications.length ? <p className="notification-empty">No timetable notifications.</p> : null}
                  </div>
                </div>
              ) : null}
            </div>
            <span className="user-avatar" aria-hidden="true">
              {(session?.user?.name || "User").split(" ").map((part) => part[0]).slice(0, 2).join("")}
            </span>
            <span>
              <strong>{session?.user?.name || "ClassOrbit User"}</strong>
              <small>{session?.user?.role || "User"}</small>
            </span>
          </div>
        </header>

        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
