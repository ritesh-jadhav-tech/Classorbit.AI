import { Link } from "react-router-dom";

const researchHighlights = [
  { label: "Domain", value: "AI-based classroom occupancy" },
  { label: "Platform", value: "Smart room allocation system" },
  { label: "Primary user", value: "College admin staff" },
  { label: "Future scope", value: "Faculty and exam coordinator portals" },
];

const modules = [
  "Central classroom inventory",
  "Class-wise timetable management",
  "Room request approval",
  "Event and exam room planning",
  "Occupancy status dashboard",
  "Smart room recommendation contract",
];

const workflow = [
  "CCTV / room input",
  "Python AI detection",
  "FastAPI service",
  "PostgreSQL records",
  "React admin dashboard",
];

function Introduction() {
  return (
    <main className="intro-page">
      <header className="intro-nav">
        <Link className="brand-lockup" to="/">
          <img alt="ClassOrbit" className="brand-logo" src="/classorbit-logo.png" />
          <span className="brand-copy">
            <strong>ClassOrbit</strong>
            <small>Smart Rooms. Smarter Allocation.</small>
          </span>
        </Link>

        <nav>
          <a href="#research">Research</a>
          <a href="#modules">Modules</a>
          <Link to="/login">Login</Link>
          <Link className="ui-button primary sm" to="/admin">
            Admin Portal
          </Link>
        </nav>
      </header>

      <section className="intro-hero">
        <div className="intro-hero-copy">
          <span className="eyebrow">AI-Based Classroom Occupancy & Smart Room Allocation System</span>
          <h1>ClassOrbit</h1>
          <p>
            ClassOrbit is a minimal college operations platform that brings classroom data,
            timetable planning, room requests, occupancy visibility, and intelligent allocation
            into one clean admin portal.
          </p>
          <div className="hero-actions">
            <Link className="ui-button primary md" to="/login">
              Login
            </Link>
            <Link className="ui-button secondary md" to="/admin">
              View Admin Portal
            </Link>
          </div>
        </div>

        <div className="intro-logo-stage">
          <img alt="ClassOrbit system logo" src="/classorbit-logo.png" />
        </div>
      </section>

      <section className="landing-section research-overview" id="research">
        <div>
          <span className="eyebrow">Research Overview</span>
          <h2>Less manual room confusion, more allocation clarity.</h2>
        </div>
        <p>
          In many colleges, classroom allocation depends on scattered timetable sheets, manual room
          checks, and delayed communication. ClassOrbit proposes an admin-first system where rooms,
          schedules, requests, events, examinations, and occupancy signals can be managed from one
          structured interface.
        </p>
      </section>

      <section className="landing-metrics">
        {researchHighlights.map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </section>

      <section className="landing-section split-section">
        <div>
          <span className="eyebrow">Problem Statement</span>
          <h2>Rooms are available, but admins often cannot see that clearly.</h2>
        </div>
        <div className="text-list">
          <p>Timetable and room data is usually fragmented across departments.</p>
          <p>Extra lecture and event requests can create double booking conflicts.</p>
          <p>Occupancy information is difficult to verify without a centralized system.</p>
          <p>Exam and seminar planning needs capacity-aware room selection.</p>
        </div>
      </section>

      <section className="landing-section split-section">
        <div>
          <span className="eyebrow">Proposed Solution</span>
          <h2>A scalable admin portal prepared for AI occupancy integration.</h2>
        </div>
        <p>
          ClassOrbit connects its administrative and faculty views to a FastAPI backend, stores
          imported timetable records in PostgreSQL, and keeps classroom schedules traceable to
          their source documents.
        </p>
      </section>

      <section className="landing-section" id="modules">
        <div className="section-title-row">
          <div>
            <span className="eyebrow">System Modules</span>
            <h2>Built around real college operations.</h2>
          </div>
        </div>
        <div className="module-grid">
          {modules.map((module) => (
            <div className="module-card" key={module}>
              <strong>{module}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section workflow-section">
        <div>
          <span className="eyebrow">Future AI Flow</span>
          <h2>Designed for a practical computer-vision backend.</h2>
        </div>
        <div className="workflow-track">
          {workflow.map((step, index) => (
            <div key={step}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section tech-section">
        <div>
          <span className="eyebrow">Technology Direction</span>
          <h2>Clean frontend now, backend-ready later.</h2>
        </div>
        <div className="tech-grid">
          <span>React</span>
          <span>FastAPI</span>
          <span>PostgreSQL</span>
          <span>OpenCV</span>
          <span>YOLO</span>
          <span>Role-based portals</span>
        </div>
      </section>
    </main>
  );
}

export default Introduction;
