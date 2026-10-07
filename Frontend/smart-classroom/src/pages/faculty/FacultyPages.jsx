import { useEffect, useMemo, useState } from "react";
import { getSession } from "../../auth/session";
import { useResource } from "../../hooks/useResource";
import { classOrbitApi } from "../../services/classOrbitApi";
import { Button, DataTable, Field, PageHeader, Section, StatCard, StatusBadge, Toolbar } from "../../components/ui";

const facultyName = () => getSession()?.user?.name || "Faculty User";

function ScheduleTimeline({ entries }) {
  if (!entries.length) return <div className="faculty-empty"><strong>No sessions scheduled.</strong><span>Your day is currently clear.</span></div>;
  return <div className="faculty-schedule-list">{entries.map((entry) => (
    <article className="faculty-schedule-item" key={entry.id}>
      <time>{entry.time}</time>
      <div><strong>{entry.subject}</strong><span>{entry.classLabel} | {entry.room}</span></div>
      <StatusBadge value={entry.status} />
    </article>
  ))}</div>;
}

export function FacultyDashboard() {
  const timetable = useResource(classOrbitApi.getTimetable);
  const classrooms = useResource(classOrbitApi.getClassrooms);
  const today = new Intl.DateTimeFormat("en-US", { weekday: "long" }).format(new Date());
  const todayClasses = timetable.data.filter((entry) => entry.day === today);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Faculty workspace" title={`Welcome, ${facultyName().split(" ")[0]}`} description="Live college timetable and classroom information." />
      <div className="stats-grid faculty-stats">
        <StatCard label="Today's lectures" value={todayClasses.length} detail={`${today} schedule`} />
        <StatCard label="Weekly sessions" value={timetable.data.length} detail="Published timetable entries" tone="info" />
        <StatCard label="Mapped rooms" value={classrooms.data.filter((room) => room.lectureCount > 0).length} detail="From official timetables" tone="success" />
        <StatCard label="Total rooms" value={classrooms.data.length} detail="Backend classroom inventory" />
      </div>
      <Section title="Today's schedule" description="Published lectures and activities for today.">
        <ScheduleTimeline entries={todayClasses} />
      </Section>
    </div>
  );
}

export function FacultySchedule() {
  const [day, setDay] = useState("");
  const { data, isLoading } = useResource(classOrbitApi.getTimetable);
  const days = useMemo(() => [...new Set(data.map((entry) => entry.day))], [data]);
  const selectedDay = days.includes(day) ? day : days[0] || "";
  const entries = data.filter((entry) => entry.day === selectedDay);
  if (isLoading) return <div className="state-block"><strong>Loading timetable...</strong></div>;
  return (
    <div className="page-stack">
      <PageHeader eyebrow="Schedule" title="Published timetable" description="Live timetable entries managed by the administrator." />
      <div className="day-tabs" role="tablist" aria-label="Schedule day">
        {days.map((item) => <button className={selectedDay === item ? "active" : ""} key={item} onClick={() => setDay(item)} type="button">{item.slice(0, 3)}</button>)}
      </div>
      <Section title={selectedDay || "Schedule"} description={`${entries.length} scheduled entries.`}><ScheduleTimeline entries={entries} /></Section>
      <Section title="Weekly timetable" description="All published lectures and practical sessions.">
        <DataTable columns={[
          { key: "day", header: "Day" }, { key: "time", header: "Time" }, { key: "subject", header: "Subject" },
          { key: "classLabel", header: "Class" }, { key: "room", header: "Room" },
          { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
        ]} rows={data} getRowKey={(row) => row.id} emptyMessage="No timetable entries have been published." />
      </Section>
    </div>
  );
}

export function FacultyAvailability() {
  const { data: classrooms } = useResource(classOrbitApi.getClassrooms);
  const { data: timetable } = useResource(classOrbitApi.getTimetable);
  const dayOptions = useMemo(() => [...new Set(timetable.map((entry) => entry.day))], [timetable]);
  const [filters, setFilters] = useState({ day: "", startTime: "09:00", endTime: "10:00", capacity: "0" });
  const [availableRooms, setAvailableRooms] = useState([]);
  const [loading, setLoading] = useState(false);
  const change = (event) => setFilters({ ...filters, [event.target.name]: event.target.value });
  const selectedDay = dayOptions.includes(filters.day) ? filters.day : dayOptions[0] || "";

  useEffect(() => {
    let active = true;
    Promise.all(classrooms.map(async (room) => ({
      room,
      availability: await classOrbitApi.getAvailability({ room: room.room, day: selectedDay, startTime: filters.startTime, endTime: filters.endTime }),
    }))).then((results) => {
      if (active) setAvailableRooms(results.filter(({ room, availability }) => availability.scheduled_availability === "AVAILABLE" && (room.capacity || 0) >= Number(filters.capacity)).map(({ room }) => room));
    }).catch(() => active && setAvailableRooms([])).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [classrooms, filters.capacity, filters.endTime, filters.startTime, selectedDay]);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Room finder" title="Find an available classroom" description="Availability is calculated from stored timetable and allocation data." />
      <Toolbar>
        <Field label="Day" name="day" options={dayOptions} value={selectedDay} onChange={change} />
        <Field label="Start time" name="startTime" type="time" value={filters.startTime} onChange={change} />
        <Field label="End time" name="endTime" type="time" value={filters.endTime} onChange={change} />
        <Field label="Minimum capacity" name="capacity" type="number" min="0" value={filters.capacity} onChange={change} />
      </Toolbar>
      <Section title="Available rooms" description={loading ? "Checking planned schedules..." : `${availableRooms.length} rooms available.`}>
        <div className="classroom-tile-grid">{availableRooms.map((room) => (
          <div className="classroom-tile" key={room.id}><strong>{room.room}</strong><span>{room.name}</span><small>{room.capacity ? `${room.capacity} seats` : "Capacity not set"}</small></div>
        ))}</div>
      </Section>
    </div>
  );
}

export function FacultyRequests() {
  return <div className="page-stack"><PageHeader eyebrow="My requests" title="Room requests" description="No room-request backend has been connected yet." /><Section title="Request history" description="Only persisted backend requests will appear here."><DataTable columns={[{ key: "id", header: "Request" }, { key: "status", header: "Status" }]} rows={[]} getRowKey={(row) => row.id} emptyMessage="No persisted room requests." /></Section></div>;
}

export function FacultyProfile() {
  const user = getSession()?.user || {};
  const initials = (user.name || "Faculty User").split(" ").map((part) => part[0]).slice(0, 2).join("");
  return <div className="page-stack"><PageHeader eyebrow="Faculty profile" title={user.name || "Faculty User"} description="Your authenticated ClassOrbit account." /><Section title="Profile information"><div className="profile-identity"><span className="profile-avatar">{initials}</span><div><h2>{user.name || "Faculty User"}</h2><p>{user.role || "Faculty"}</p></div></div><div className="detail-list inline"><span>Email</span><strong>{user.email || "Not provided"}</strong><span>Department</span><strong>{user.department || "Not assigned"}</strong></div></Section></div>;
}

export function FacultySettings() {
  const [saved, setSaved] = useState(false);
  return <div className="page-stack"><PageHeader eyebrow="Preferences" title="Settings" description="Manage faculty workspace preferences." /><Section title="Notifications"><form className="settings-form" onSubmit={(event) => { event.preventDefault(); setSaved(true); }}><label className="toggle-row"><span><strong>Schedule changes</strong><small>Notify me when timetable imports are processed.</small></span><input defaultChecked type="checkbox" /></label>{saved ? <p className="success-message">Preferences saved.</p> : null}<Button type="submit">Save Preferences</Button></form></Section></div>;
}
