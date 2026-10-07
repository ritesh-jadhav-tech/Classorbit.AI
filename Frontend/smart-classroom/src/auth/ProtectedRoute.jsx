import { Navigate, Outlet, useLocation } from "react-router-dom";
import { hasRole } from "./session";

function ProtectedRoute({ allowedRoles }) {
  const location = useLocation();

  if (!hasRole(allowedRoles)) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
