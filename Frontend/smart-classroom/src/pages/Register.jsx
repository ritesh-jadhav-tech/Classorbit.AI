import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button, Field } from "../components/ui";
import { defaultPathForRole, roles, setSession } from "../auth/session";
import { registerWithBackend } from "../services/classOrbitApi";

function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    role: roles.faculty,
  });
  const [error, setError] = useState("");

  const handleChange = (event) => {
    setFormData({ ...formData, [event.target.name]: event.target.value });
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      const session = await registerWithBackend({
        name: formData.name,
        email: formData.email,
        password: formData.password,
        role: formData.role === roles.admin ? "ADMIN" : formData.role === roles.faculty ? "FACULTY" : "EXAM_COORDINATOR",
      });
      setSession(session);
      navigate(defaultPathForRole(session.user.role), { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <img alt="ClassOrbit" className="brand-logo" src="/classorbit-logo.png" />
          <div>
            <strong>ClassOrbit</strong>
            <small>Role-based account</small>
          </div>
        </div>

        <div className="auth-copy">
          <h1>Create Account</h1>
          <p>Register a frontend test account for the prototype.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <Field label="Full Name" name="name" onChange={handleChange} required value={formData.name} />
          <Field label="Email Address" name="email" onChange={handleChange} required type="email" value={formData.email} />
          <Field label="Password" name="password" onChange={handleChange} required type="password" value={formData.password} />
          <Field label="Confirm Password" name="confirmPassword" onChange={handleChange} required type="password" value={formData.confirmPassword} />
          <Field label="Role" name="role" onChange={handleChange} options={[roles.admin, roles.faculty, roles.examCoordinator]} value={formData.role} />
          {error ? <p className="field-error">{error}</p> : null}
          <Button type="submit">Create Account</Button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </section>
    </main>
  );
}

export default Register;
