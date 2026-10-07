import { Link } from "react-router-dom";
import { PageHeader, Section } from "../components/ui";

function PortalPlaceholder({ portal }) {
  return (
    <main className="standalone-page">
      <PageHeader
        description="This portal is reserved in the routing architecture and can be implemented without changing the admin area."
        eyebrow="Future Portal"
        title={`${portal} Portal`}
      />
      <Section title="Planned Scope">
        <p className="muted-copy">
          The current phase focuses on the admin portal. Faculty and exam coordinator workflows are intentionally kept out of admin routing.
        </p>
        <Link className="ui-button secondary md" to="/admin">
          Back to Admin
        </Link>
      </Section>
    </main>
  );
}

export default PortalPlaceholder;
