export const roles = {
  admin: "Admin",
  faculty: "Faculty",
  examCoordinator: "Exam Coordinator",
};

const backendRoles = {
  ADMIN: roles.admin,
  FACULTY: roles.faculty,
  EXAM_COORDINATOR: roles.examCoordinator,
};

const storageKey = "classorbit-session";

export function getSession() {
  try {
    const stored = window.localStorage.getItem(storageKey);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function setSession(session) {
  window.localStorage.setItem(storageKey, JSON.stringify(session));
}

export function clearSession() {
  window.localStorage.removeItem(storageKey);
}

export function normalizeBackendUser(user) {
  const rawRole = typeof user?.role === "string" ? user.role : user?.role?.name;
  return {
    ...user,
    role: backendRoles[rawRole] || rawRole || roles.faculty,
    department: user?.department || "Computer Science",
  };
}

export function defaultPathForRole(role) {
  if (role === roles.admin) return "/admin";
  if (role === roles.faculty) return "/faculty";
  return "/exam-coordinator";
}

export function hasRole(allowedRoles) {
  const session = getSession();
  return allowedRoles.includes(session?.user?.role);
}
