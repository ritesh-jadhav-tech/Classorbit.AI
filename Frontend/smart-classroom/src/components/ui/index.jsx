import { Link } from "react-router-dom";

const statusTone = {
  Active: "success",
  ACTIVE: "success",
  Available: "success",
  Approved: "success",
  ALLOCATED: "success",
  COMPLETED: "success",
  Occupied: "danger",
  Rejected: "danger",
  FAILED: "danger",
  Pending: "warning",
  NEEDS_REVIEW: "warning",
  Scheduled: "info",
  Invited: "info",
  UNKNOWN: "neutral",
  AVAILABLE: "success",
  OCCUPIED: "danger",
  LECTURE: "info",
  Cancelled: "neutral",
  Maintenance: "neutral",
};

export function Button({
  children,
  className = "",
  tone = "primary",
  size = "md",
  as: Component = "button",
  ...props
}) {
  return (
    <Component className={`ui-button ${tone} ${size} ${className}`} {...props}>
      {children}
    </Component>
  );
}

export function LinkButton({ children, to, tone = "primary", size = "md" }) {
  return (
    <Button as={Link} to={to} tone={tone} size={size}>
      {children}
    </Button>
  );
}

export function StatusBadge({ value, tone }) {
  const badgeTone = tone || statusTone[value] || statusTone[String(value).toUpperCase()] || "neutral";

  return <span className={`status-badge ${badgeTone}`}>{value}</span>;
}

export function PageHeader({ title, eyebrow, description, actions, meta }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
        {meta ? <div className="page-meta">{meta}</div> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </div>
  );
}

export function StatCard({ label, value, detail, tone = "neutral" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

export function Section({ title, description, action, children, className = "" }) {
  return (
    <section className={`surface-section ${className}`}>
      {(title || description || action) && (
        <div className="section-header">
          <div>
            {title ? <h2>{title}</h2> : null}
            {description ? <p>{description}</p> : null}
          </div>
          {action ? <div>{action}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}

export function Toolbar({ children }) {
  return <div className="toolbar">{children}</div>;
}

export function Field({
  label,
  name,
  type = "text",
  value,
  onChange,
  placeholder,
  options,
  required,
  min,
}) {
  return (
    <label className="field">
      <span>
        {label}
        {required ? <b> *</b> : null}
      </span>
      {options ? (
        <select name={name} value={value} onChange={onChange} required={required}>
          {options.map((option) => (
            <option
              key={typeof option === "object" ? option.value : option}
              value={typeof option === "object" ? option.value : option}
            >
              {typeof option === "object" ? option.label : option}
            </option>
          ))}
        </select>
      ) : (
        <input
          min={min}
          name={name}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          type={type}
          value={value}
        />
      )}
    </label>
  );
}

export function SearchField({ value, onChange, placeholder = "Search..." }) {
  return (
    <label className="search-field">
      <span aria-hidden="true">/</span>
      <input value={value} onChange={onChange} placeholder={placeholder} type="search" />
    </label>
  );
}

export function DataTable({ columns, rows, getRowKey, emptyMessage, onRowClick }) {
  if (!rows.length) {
    return <EmptyState title={emptyMessage || "No records found."} />;
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={getRowKey(row)}
              className={onRowClick ? "clickable-row" : ""}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((column) => (
                <td key={column.key} data-label={column.header}>
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Modal({ title, description, children, onClose, className = "" }) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className={`modal-panel ${className}`} onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2>{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          <button aria-label="Close" className="icon-button" onClick={onClose} type="button">
            x
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Drawer({ title, description, children, onClose }) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <aside className="drawer-panel" onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2>{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          <button aria-label="Close" className="icon-button" onClick={onClose} type="button">
            x
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}

export function LoadingState({ title = "Loading data..." }) {
  return (
    <div className="state-block">
      <span className="spinner" aria-hidden="true" />
      <strong>{title}</strong>
    </div>
  );
}

export function EmptyState({ title = "No records found.", description }) {
  return (
    <div className="state-block">
      <strong>{title}</strong>
      {description ? <p>{description}</p> : null}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong.", description }) {
  return (
    <div className="state-block error">
      <strong>{title}</strong>
      {description ? <p>{description}</p> : null}
    </div>
  );
}

export function FormActions({ onCancel, submitLabel = "Save" }) {
  return (
    <div className="form-actions">
      <Button onClick={onCancel} tone="secondary" type="button">
        Cancel
      </Button>
      <Button type="submit">{submitLabel}</Button>
    </div>
  );
}
