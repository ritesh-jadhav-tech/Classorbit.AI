import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { defaultPathForRole, roles, setSession } from "../auth/session";
import { loginWithBackend } from "../services/classOrbitApi";
import { Button, Field } from "../components/ui";

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [formData, setFormData] = useState({
    email: "admin@classorbit.edu",
    password: "admin123",
    role: roles.admin,
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const from = location.state?.from?.pathname || "/admin";

  const handleChange = (event) => {
    setFormData({ ...formData, [event.target.name]: event.target.value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const session = await loginWithBackend(formData.email, formData.password);
      if (session.user.role !== formData.role) throw new Error(`This account has ${session.user.role} access.`);
      setSession(session);
      navigate(location.state?.from ? from : defaultPathForRole(session.user.role), { replace: true });
    } catch (requestError) {
      if (requestError instanceof TypeError) {
        const session = {
          user: {
            name: formData.role === roles.admin ? "Admin User" : "Dr. Rajesh Patil",
            email: formData.email,
            role: formData.role,
            department: formData.role === roles.admin ? "Administration" : "Computer Science",
          },
          demoMode: true,
        };
        setSession(session);
        navigate(defaultPathForRole(formData.role), { replace: true });
      } else {
        setError(requestError.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <img alt="ClassOrbit" className="brand-logo" src="/classorbit-logo.png" />
          <div>
            <strong>ClassOrbit</strong>
            <small>Smart Rooms. Smarter Allocation.</small>
          </div>
        </div>

        <div className="auth-copy">
          <h1>Sign in</h1>
          <p>Access your role-based ClassOrbit workspace.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <Field label="Email Address" name="email" onChange={handleChange} required type="email" value={formData.email} />
          <Field label="Password" name="password" onChange={handleChange} required type="password" value={formData.password} />
          <Field label="Role" name="role" onChange={handleChange} options={[roles.admin, roles.faculty, roles.examCoordinator]} value={formData.role} />
          {error ? <p className="field-error">{error}</p> : null}
          <Button disabled={isSubmitting} type="submit">{isSubmitting ? "Signing in..." : "Login"}</Button>
        </form>

        <p className="auth-footer">
          Need a test account? <Link to="/register">Create one</Link>
        </p>
      </section>
    </main>
  );
}

export default Login;
