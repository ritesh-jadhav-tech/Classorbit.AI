import { useMemo, useState } from "react";
import { AlertTriangle, Check, Download, FileSpreadsheet, MoreHorizontal, Pencil, Plus, Trash2, Upload } from "lucide-react";
import { getSession } from "../../auth/session";
import { useResource } from "../../hooks/useResource";
import { classOrbitApi } from "../../services/classOrbitApi";
import {
  Button,
  DataTable,
  Drawer,
  ErrorState,
  Field,
  FormActions,
  LinkButton,
  LoadingState,
  Modal,
  PageHeader,
  SearchField,
  Section,
  StatCard,
  StatusBadge,
  Toolbar,
} from "../../components/ui";

const departments = ["Computer Science", "Information Technology", "Artificial Intelligence", "Data Science"];
const semesters = ["3rd Semester", "5th Semester", "6th Semester"];
const supportedTimetableExtensions = [
  ".pdf", ".xlsx", ".xls", ".xlsm", ".csv", ".docx",
  ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp",
];
const formatTime = (value) =>
  new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));

export function Dashboard() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getAdminOverview, {
    classrooms: [],
    allocations: [],
    requests: [],
    timetable: [],
    quickActions: [],
  });

  const stats = useMemo(() => {
    const available = data.classrooms.filter((room) => room.status === "Available").length;
    const occupied = data.classrooms.filter((room) => room.status === "Occupied").length;
    const pending = data.requests.filter((request) => request.status === "Pending").length;

    return [
      { label: "Total Classrooms", value: data.classrooms.length, detail: "Across active buildings" },
      { label: "Available", value: available, detail: "Open now", tone: "success" },
      { label: "Occupied", value: occupied, detail: "In use or detected occupied", tone: "danger" },
      { label: "Pending Requests", value: pending, detail: "Need admin decision", tone: "warning" },
    ];
  }, [data]);

  if (isLoading) return <LoadingState title="Loading admin overview..." />;
  if (isError) return <ErrorState description={error} title="Unable to load dashboard." />;

  return (
    <div className="page-stack">
      <PageHeader
        description="Manage today's academic spaces and classroom allocations."
        eyebrow="Overview"
        title="Good morning, Admin"
      />

      <div className="stats-grid">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <div className="dashboard-grid">
        <Section description="Current operating view for rooms in use." title="Today's Classroom Status">
          <DataTable
            columns={[
              { key: "room", header: "Room" },
              { key: "time", header: "Time" },
              { key: "activity", header: "Activity" },
              { key: "department", header: "Department" },
              { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
            ]}
            emptyMessage="No classroom status data found for today."
            getRowKey={(row) => row.id}
            rows={data.allocations.slice(0, 5)}
          />
        </Section>

        <Section description="Requests waiting for approval or room review." title="Pending Room Requests">
          <DataTable
            columns={[
              { key: "id", header: "ID" },
              { key: "requestedBy", header: "Requested By" },
              { key: "purpose", header: "Purpose" },
              { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
            ]}
            emptyMessage="No pending room requests."
            getRowKey={(row) => row.id}
            rows={data.requests.filter((request) => request.status === "Pending")}
          />
        </Section>
      </div>

      <div className="dashboard-grid compact">
        <Section description="Next scheduled academic allocations." title="Upcoming Allocations">
          <div className="timeline-list">
            {data.timetable.slice(0, 4).map((entry) => (
              <div className="timeline-item" key={entry.id}>
                <time>{entry.time}</time>
                <div>
                  <strong>{entry.subject}</strong>
                  <span>
                    {entry.room} | {entry.faculty}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section description="Common admin actions." title="Quick Actions">
          <div className="quick-actions">
            {data.quickActions.map((action) => (
              <LinkButton key={action.label} size="sm" to={action.to} tone="secondary">
                {action.label}
              </LinkButton>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}

export function Timetable() {
  const { data: structures, setData: setStructures, isLoading, isError, error } = useResource(classOrbitApi.getTimetableStructures);
  const { data: editableClassrooms } = useResource(classOrbitApi.getBackendClassrooms);
  const [filters, setFilters] = useState({
    timetableId: "all",
    department: "All Departments",
    year: "All Years",
    day: "All Days",
    time: "All Times",
  });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadState, setUploadState] = useState({ status: "idle", message: "" });
  const [, setUploadProgress] = useState(0);
  const [showImport, setShowImport] = useState(false);
  const [importRecord, setImportRecord] = useState(null);
  const [importReviews, setImportReviews] = useState([]);
  const [selectedReview, setSelectedReview] = useState(null);
  const [reviewForm, setReviewForm] = useState(null);
  const [reviewState, setReviewState] = useState({ status: "idle", message: "" });
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [manualForm, setManualForm] = useState({ timetable_id: "", day_of_week: "Monday", start_time: "", end_time: "", subject_text: "", classroom_id: "" });
  const [manualState, setManualState] = useState({ status: "idle", message: "" });
  const [editingEntry, setEditingEntry] = useState(null);
  const [viewingEntry, setViewingEntry] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [editState, setEditState] = useState({ status: "idle", message: "" });

  const activeStructures = useMemo(
    () => filters.timetableId === "all"
      ? structures
      : structures.filter((structure) => structure.classKey === filters.timetableId),
    [filters.timetableId, structures],
  );
  const data = useMemo(() => activeStructures.flatMap((structure) => structure.entries), [activeStructures]);
  const days = useMemo(
    () => [...new Set(activeStructures.flatMap((structure) => structure.columns))],
    [activeStructures],
  );
  const attributeKeys = useMemo(
    () => [...new Set(activeStructures.flatMap((structure) => structure.attributeKeys))],
    [activeStructures],
  );

  const classOptions = useMemo(
    () => [...structures.reduce((grouped, structure) => {
      const current = grouped.get(structure.classKey) || {
        value: structure.classKey,
        label: structure.classLabel,
        entryCount: 0,
      };
      current.entryCount += structure.entries.length;
      grouped.set(structure.classKey, current);
      return grouped;
    }, new Map()).values()].sort((left, right) => left.label.localeCompare(right.label)),
    [structures],
  );
  const yearOptions = useMemo(
    () => [...new Set(data.map((entry) => entry.academicYear))].sort(),
    [data],
  );
  const departmentOptions = useMemo(
    () => [...new Set(data.map((entry) => entry.department).filter((value) => value !== "Not specified"))].sort(),
    [data],
  );
  const timeOptions = useMemo(
    () => [...new Set(activeStructures.flatMap((structure) => structure.timeSlots.map((slot) => slot.time)))],
    [activeStructures],
  );
  const rows = useMemo(
    () => data.filter((entry) => {
      const classMatch = filters.timetableId === "all" || entry.classKey === filters.timetableId;
      const yearMatch = filters.year === "All Years" || entry.academicYear === filters.year;
      const departmentMatch = filters.department === "All Departments" || entry.department === filters.department;
      const dayMatch = filters.day === "All Days" || entry.day === filters.day;
      const timeMatch = filters.time === "All Times" || entry.time === filters.time;
      return classMatch && departmentMatch && yearMatch && dayMatch && timeMatch;
    }),
    [data, filters],
  );

  const weeklyRows = useMemo(
    () => (filters.time === "All Times" ? timeOptions : [filters.time]).map((time) => ({
      time,
      days: Object.fromEntries(days.map((day) => [day, rows.filter((entry) => entry.day === day && entry.time === time)])),
    })),
    [days, filters.time, rows, timeOptions],
  );
  const unresolvedReviews = useMemo(
    () => importReviews.filter((review) => review.validation_status !== "VALID"),
    [importReviews],
  );
  const pendingPublicationReviews = useMemo(
    () => importReviews.filter((review) => (
      !review.timetable_entry_id
      && !["REJECTED", "IGNORED", "INVALID"].includes(review.action)
    )),
    [importReviews],
  );

  const handleFilterChange = (event) => setFilters({ ...filters, [event.target.name]: event.target.value });
  const openEntryEditor = (entry) => {
    setEditingEntry(entry);
    setEditForm({
      subject: entry.subject,
      roomHint: entry.roomHint,
      facultyText: entry.facultyText,
    });
    setEditState({ status: "idle", message: "" });
  };
  const closeEntryEditor = () => {
    if (editState.status === "saving") return;
    setEditingEntry(null);
    setEditForm(null);
    setEditState({ status: "idle", message: "" });
  };
  const handleEditChange = (event) => setEditForm({ ...editForm, [event.target.name]: event.target.value });
  const handleEntryUpdate = async (event) => {
    event.preventDefault();
    setEditState({ status: "saving", message: "" });
    try {
      await classOrbitApi.updateTimetableEntry(editingEntry.id, {
        subject_text: editForm.subject,
        room_hint: editForm.roomHint || null,
        faculty_text: editForm.facultyText || null,
      });
      setStructures(await classOrbitApi.getTimetableStructures());
      setEditingEntry(null);
      setEditForm(null);
      setEditState({ status: "idle", message: "" });
    } catch (requestError) {
      setEditState({ status: "error", message: requestError.message });
    }
  };
  const handleEntryDelete = async () => {
    setEditState({ status: "saving", message: "" });
    try {
      await classOrbitApi.deleteTimetableEntry(editingEntry.id);
      setStructures(await classOrbitApi.getTimetableStructures());
      setEditingEntry(null);
      setEditForm(null);
      setEditState({ status: "idle", message: "" });
    } catch (requestError) {
      setEditState({ status: "error", message: requestError.message });
    }
  };
  const resetImportDialog = () => {
    setUploadFile(null);
    setUploadProgress(0);
    setUploadState({ status: "idle", message: "" });
    setImportRecord(null);
    setImportReviews([]);
    setSelectedReview(null);
    setReviewState({ status: "idle", message: "" });
  };
  const openImportDialog = () => {
    resetImportDialog();
    setShowImport(true);
  };
  const processTimetableFile = async (file) => {
    setUploadFile(file);
    setImportRecord(null);
    setImportReviews([]);
    setSelectedReview(null);
    setUploadProgress(0);
    setUploadState({ status: "uploading", message: "Uploading timetable..." });
    try {
      const imported = await classOrbitApi.uploadTimetable(file, (progress) => {
        setUploadProgress(progress);
        setUploadState({
          status: "uploading",
          message: progress < 100 ? `Uploading file... ${progress}%` : "Extracting classes, subjects, rooms, and time slots...",
        });
      });
      window.dispatchEvent(new CustomEvent("classorbit:imports-updated"));
      const summary = imported.summary_json || {};
      setImportRecord(imported);
      if (imported.status === "FAILED") {
        setUploadState({ status: "error", message: imported.error_message || "The timetable could not be imported." });
        return;
      }
      setImportReviews(await classOrbitApi.getImportReviews(imported.id));
      setStructures(await classOrbitApi.getTimetableStructures());
      setUploadState({
        status: summary.needs_review || summary.invalid ? "review" : "success",
        message: summary.needs_review || summary.invalid
          ? "Extraction completed with issues that need review."
          : "Timetable extracted and saved successfully.",
      });
    } catch (requestError) {
      setUploadState({ status: "error", message: requestError.message });
    }
  };
  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    if (!file) return;
    const extension = file.name.toLowerCase().match(/\.[^.]+$/)?.[0];
    if (!supportedTimetableExtensions.includes(extension)) {
      setUploadFile(file);
      setUploadState({ status: "error", message: "Choose a PDF, Excel, image, Word, or CSV timetable file." });
      return;
    }
    processTimetableFile(file);
  };
  const openReviewEditor = (review) => {
    setSelectedReview(review);
    setReviewForm({
      subject_text: review.subject_text || "",
      room_hint: review.room_hint || "",
      day_of_week: review.day_of_week || "Monday",
      start_time: review.start_time || "",
      end_time: review.end_time || "",
      division: review.division || "",
    });
    setReviewState({ status: "idle", message: "" });
  };
  const handleReviewChange = (event) => setReviewForm({ ...reviewForm, [event.target.name]: event.target.value });
  const saveReview = async (action = "EDITED") => {
    setReviewState({ status: "saving", message: "" });
    try {
      const room = editableClassrooms.find((item) => (
        item.room_number.toLowerCase() === reviewForm.room_hint.trim().toLowerCase()
        || (item.display_name || "").toLowerCase() === reviewForm.room_hint.trim().toLowerCase()
      ));
      await classOrbitApi.updateImportReview(importRecord.id, selectedReview.id, {
        ...reviewForm,
        room_hint: reviewForm.room_hint || null,
        matched_classroom_id: room?.id || null,
        action,
      });
      setImportReviews(await classOrbitApi.getImportReviews(importRecord.id));
      setSelectedReview(null);
      setReviewForm(null);
      setReviewState({ status: "idle", message: "" });
    } catch (requestError) {
      setReviewState({ status: "error", message: requestError.message });
    }
  };
  const handleConfirmImport = async () => {
    setReviewState({ status: "saving", message: "Publishing timetable..." });
    try {
      const result = await classOrbitApi.confirmImport(importRecord.id);
      if (result.unresolved_review_records) {
        setImportReviews(await classOrbitApi.getImportReviews(importRecord.id));
        setReviewState({ status: "error", message: `${result.unresolved_review_records} entries still require review.` });
        return;
      }
      setStructures(await classOrbitApi.getTimetableStructures());
      setReviewState({ status: "success", message: `${result.created_entries} entries published.` });
      setShowImport(false);
      setUploadFile(null);
      setImportRecord(null);
      setImportReviews([]);
      setUploadState({ status: "success", message: "Timetable published successfully." });
      window.dispatchEvent(new CustomEvent("classorbit:imports-updated"));
    } catch (requestError) {
      setReviewState({ status: "error", message: requestError.message });
    }
  };
  const handleTemplateDownload = async () => {
    try {
      await classOrbitApi.downloadTimetableTemplate();
    } catch (requestError) {
      setUploadState({ status: "error", message: requestError.message });
    }
  };
  const openManualEntry = () => {
    setManualForm({ ...manualForm, timetable_id: manualForm.timetable_id || structures[0]?.id || "" });
    setManualState({ status: "idle", message: "" });
    setShowManualEntry(true);
  };
  const handleManualChange = (event) => setManualForm({ ...manualForm, [event.target.name]: event.target.value });
  const handleManualSubmit = async (event) => {
    event.preventDefault();
    setManualState({ status: "saving", message: "" });
    try {
      const slot = await classOrbitApi.createTimeSlot({ start_time: manualForm.start_time, end_time: manualForm.end_time });
      const classroom = editableClassrooms.find((room) => room.id === manualForm.classroom_id);
      await classOrbitApi.createTimetableEntry({
        timetable_id: manualForm.timetable_id,
        day_of_week: manualForm.day_of_week,
        time_slot_id: slot.id,
        subject_text: manualForm.subject_text,
        classroom_id: classroom?.id || null,
        room_hint: classroom?.room_number || null,
        location_type: classroom ? "CLASSROOM" : "UNKNOWN",
        mapping_status: classroom ? "MATCHED" : "NONE",
      });
      setStructures(await classOrbitApi.getTimetableStructures());
      setShowManualEntry(false);
      setManualState({ status: "idle", message: "" });
    } catch (requestError) {
      setManualState({ status: "error", message: requestError.message });
    }
  };

  if (isLoading) return <LoadingState title="Loading timetable..." />;
  if (isError) return <ErrorState description={error} title="Unable to load timetable." />;

  return (
    <div className="page-stack">
      <PageHeader
        actions={
          <div className="page-actions">
            <Button onClick={handleTemplateDownload} tone="secondary" type="button">
              <Download aria-hidden="true" size={16} /> Download Template
            </Button>
            <Button onClick={openImportDialog} type="button">
              <Upload aria-hidden="true" size={16} /> Import Timetable
            </Button>
            <Button onClick={openManualEntry} tone="secondary" type="button">
              <Plus aria-hidden="true" size={16} /> Add Manually
            </Button>
          </div>
        }
        description="Upload a timetable and view each extracted class schedule separately."
        eyebrow="Academic"
        title="Timetable Management"
      />

      {showImport ? (
        <Modal
          className="import-timetable-modal"
          description={uploadState.status === "uploading"
            ? "Please wait while ClassOrbit reads and stores the timetable."
            : importRecord || uploadState.status === "error"
              ? "Extraction results for the selected timetable file."
              : "Choose a timetable file. Extraction starts immediately after selection."}
          onClose={() => uploadState.status !== "uploading" && setShowImport(false)}
          title={uploadState.status === "uploading" ? "Extracting Timetable" : importRecord || uploadState.status === "error" ? "Import Result" : "Import Timetable"}
        >
          <div className="import-workflow">
            {uploadState.status === "uploading" ? (
              <div className="import-processing" role="status">
                <span className="spinner import-processing-spinner" aria-hidden="true" />
                <strong>{uploadFile?.name}</strong>
                <p>{uploadState.message}</p>
              </div>
            ) : importRecord || uploadState.status === "error" ? (
              <>
                <div className={`import-result-heading ${uploadState.status}`}>
                  {uploadState.status === "success" ? <Check aria-hidden="true" size={28} /> : <AlertTriangle aria-hidden="true" size={28} />}
                  <div>
                    <strong>{uploadState.status === "success" ? "Timetable imported successfully" : uploadState.status === "review" ? "Import completed with issues" : "Timetable import failed"}</strong>
                    <span>{uploadFile?.name}</span>
                    <p>{uploadState.message}</p>
                  </div>
                </div>
                {importRecord ? (
                  <div className="import-summary-grid">
                    {[
                      ["Extracted", importRecord.summary_json.generated_timetable_entries || 0],
                      ["Published", importRecord.summary_json.valid || 0],
                      ["Classes", importRecord.summary_json.recognized_entities?.classes?.length || 0],
                      ["Needs Review", unresolvedReviews.length],
                    ].map(([label, value]) => (
                      <div key={label}><span>{label}</span><strong>{value}</strong></div>
                    ))}
                  </div>
                ) : null}
                {unresolvedReviews.length ? (
                  <div className="import-issue-list">
                    <strong>Entries requiring attention</strong>
                    {unresolvedReviews.slice(0, 8).map((review) => (
                      <button key={review.id} onClick={() => openReviewEditor(review)} type="button">
                        <span>{review.subject_text || "Missing subject"}</span>
                        <small>{[review.class_name, review.division, review.day_of_week, review.warning].filter(Boolean).join(" | ")}</small>
                      </button>
                    ))}
                    {unresolvedReviews.length > 8 ? <p>{unresolvedReviews.length - 8} more entries also need review.</p> : null}
                  </div>
                ) : null}
                {importRecord?.summary_json.warnings?.length ? (
                  <div className="import-warning-list" role="status">
                    {importRecord.summary_json.warnings.slice(0, 5).map((warning) => <p key={warning}>{warning}</p>)}
                  </div>
                ) : null}
                {reviewState.message ? <p className={reviewState.status === "error" ? "field-error" : "field-success"}>{reviewState.message}</p> : null}
                <div className="form-actions">
                  {uploadState.status === "error" ? (
                    <Button onClick={resetImportDialog} type="button">Choose another file</Button>
                  ) : unresolvedReviews.length ? (
                    <>
                      <Button onClick={() => setShowImport(false)} tone="secondary" type="button">Close</Button>
                      <Button disabled type="button"><AlertTriangle aria-hidden="true" size={16} /> Resolve Issues Above</Button>
                    </>
                  ) : pendingPublicationReviews.length ? (
                    <>
                      <Button onClick={() => setShowImport(false)} tone="secondary" type="button">Close</Button>
                      <Button disabled={reviewState.status === "saving"} onClick={handleConfirmImport} type="button">
                        <Check aria-hidden="true" size={16} /> Confirm & Publish
                      </Button>
                    </>
                  ) : (
                    <Button onClick={() => setShowImport(false)} type="button"><Check aria-hidden="true" size={16} /> Done</Button>
                  )}
                </div>
              </>
            ) : (
              <label className="import-file-picker">
                <FileSpreadsheet aria-hidden="true" size={34} />
                <strong>Choose timetable file</strong>
                <span>Excel, PDF, image, Word, or CSV</span>
                <input accept=".pdf,.xlsx,.xls,.xlsm,.csv,.docx,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp" onChange={handleFileChange} type="file" />
              </label>
            )}
          </div>
        </Modal>
      ) : null}

      {selectedReview && reviewForm ? (
        <Modal
          description={`${selectedReview.source_sheet || "Timetable"} | ${selectedReview.source_cell_reference || "Imported entry"}`}
          onClose={() => reviewState.status !== "saving" && setSelectedReview(null)}
          title="Review imported entry"
        >
          <div className="modal-form">
            <div className="form-grid edit-entry-grid">
              <Field label="Subject / Activity" name="subject_text" onChange={handleReviewChange} required value={reviewForm.subject_text} />
              <label className="field">
                <span>Classroom / Lab</span>
                <select name="room_hint" onChange={handleReviewChange} value={reviewForm.room_hint}>
                  <option value="">No classroom</option>
                  {reviewForm.room_hint && !editableClassrooms.some((room) => room.room_number === reviewForm.room_hint) ? <option value={reviewForm.room_hint}>{reviewForm.room_hint} (unmatched)</option> : null}
                  {editableClassrooms.map((room) => <option key={room.id} value={room.room_number}>{room.room_number}{room.display_name ? ` | ${room.display_name}` : ""}</option>)}
                </select>
              </label>
              <Field label="Day" name="day_of_week" onChange={handleReviewChange} options={["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]} value={reviewForm.day_of_week} />
              <Field label="Start Time" name="start_time" onChange={handleReviewChange} type="time" value={reviewForm.start_time} />
              <Field label="End Time" name="end_time" onChange={handleReviewChange} type="time" value={reviewForm.end_time} />
              <Field label="Division" name="division" onChange={handleReviewChange} value={reviewForm.division} />
            </div>
            {selectedReview.warning ? <p className="field-error">{selectedReview.warning}</p> : null}
            {reviewState.status === "error" ? <p className="field-error">{reviewState.message}</p> : null}
            <div className="form-actions">
              <Button onClick={() => setSelectedReview(null)} tone="secondary" type="button">Cancel</Button>
              <Button disabled={reviewState.status === "saving"} onClick={() => saveReview("ACCEPTED")} tone="secondary" type="button">Accept As Is</Button>
              <Button disabled={reviewState.status === "saving"} onClick={() => saveReview("EDITED")} type="button">Save Correction</Button>
            </div>
          </div>
        </Modal>
      ) : null}

      {showManualEntry ? (
        <Modal description="Add one activity to an existing timetable." onClose={() => setShowManualEntry(false)} title="Add timetable entry">
          <form className="modal-form" onSubmit={handleManualSubmit}>
            <div className="form-grid edit-entry-grid">
              <label className="field">
                <span>Class / Division *</span>
                <select name="timetable_id" onChange={handleManualChange} required value={manualForm.timetable_id}>
                  <option value="">Select timetable</option>
                  {structures.map((structure) => <option key={structure.id} value={structure.id}>{structure.classLabel}</option>)}
                </select>
              </label>
              <Field label="Subject / Activity" name="subject_text" onChange={handleManualChange} required value={manualForm.subject_text} />
              <Field label="Day" name="day_of_week" onChange={handleManualChange} options={["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]} value={manualForm.day_of_week} />
              <Field label="Start Time" name="start_time" onChange={handleManualChange} required type="time" value={manualForm.start_time} />
              <Field label="End Time" name="end_time" onChange={handleManualChange} required type="time" value={manualForm.end_time} />
              <label className="field">
                <span>Classroom / Lab</span>
                <select name="classroom_id" onChange={handleManualChange} value={manualForm.classroom_id}>
                  <option value="">No classroom</option>
                  {editableClassrooms.map((room) => <option key={room.id} value={room.id}>{room.room_number}{room.display_name ? ` | ${room.display_name}` : ""}</option>)}
                </select>
              </label>
            </div>
            {manualState.status === "error" ? <p className="field-error">{manualState.message}</p> : null}
            <FormActions onCancel={() => setShowManualEntry(false)} submitLabel={manualState.status === "saving" ? "Saving..." : "Add entry"} />
          </form>
        </Modal>
      ) : null}

      <Section
        description="Choose one class and division, or compare all imported schedules."
        title="Imported Classes"
      >
        <div className="class-selector">
          {[{ value: "all", label: "All Classes" }, ...classOptions].map((option) => (
            <button
              className={filters.timetableId === option.value ? "class-chip active" : "class-chip"}
              key={option.value}
              onClick={() => setFilters({ ...filters, timetableId: option.value })}
              type="button"
            >
              <strong>{option.label}</strong>
              <span>{option.value === "all" ? structures.reduce((total, item) => total + item.entries.length, 0) : option.entryCount} entries</span>
            </button>
          ))}
        </div>
      </Section>

      <Toolbar>
        <Field label="Class / Division" name="timetableId" onChange={handleFilterChange} options={[{ value: "all", label: "All Classes" }, ...classOptions]} value={filters.timetableId} />
        <Field label="Department" name="department" onChange={handleFilterChange} options={["All Departments", ...departmentOptions]} value={filters.department} />
        <Field label="Academic Year" name="year" onChange={handleFilterChange} options={["All Years", ...yearOptions]} value={filters.year} />
        <Field label="Week / Day" name="day" onChange={handleFilterChange} options={["All Days", ...days]} value={filters.day} />
        <Field label="Time Slot" name="time" onChange={handleFilterChange} options={["All Times", ...timeOptions]} value={filters.time} />
      </Toolbar>

      <Section description="Each cell can contain multiple subject or room options extracted from the official document." title="Weekly Timetable">
        <div className="timetable-grid-scroll">
          <table className="weekly-timetable">
            <thead>
              <tr>
                <th>Time</th>
                {days.map((day) => <th key={day}>{day}</th>)}
              </tr>
            </thead>
            <tbody>
              {weeklyRows.map((row) => (
                <tr key={row.time}>
                  <th>{row.time}</th>
                  {days.map((day) => (
                    <td key={day}>
                      {row.days[day].map((entry) => (
                        <div className="timetable-cell-entry" key={entry.id}>
                          <button
                            aria-label={`View details for ${entry.subject}`}
                            className="timetable-entry-edit"
                            onClick={() => setViewingEntry(entry)}
                            title="View timetable details"
                            type="button"
                          >
                            <MoreHorizontal aria-hidden="true" size={16} strokeWidth={2} />
                          </button>
                          <strong>{entry.subject}</strong>
                          <span>{entry.room}</span>
                          {entry.sessionType || entry.deliveryMode ? <small>{[entry.sessionType, entry.deliveryMode].filter(Boolean).join(" | ")}</small> : null}
                        </div>
                      ))}
                      {!row.days[day].length ? <span className="timetable-cell-empty">-</span> : null}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {!weeklyRows.length ? <div className="timetable-empty">No timetable entries match these filters.</div> : null}
        </div>
      </Section>

      {viewingEntry ? (
        <Modal
          description={`${viewingEntry.day} | ${viewingEntry.time}`}
          onClose={() => setViewingEntry(null)}
          title="Timetable details"
        >
          <div className="entry-detail-body">
            <div className="entry-detail-grid">
              {[
                ["Subject", viewingEntry.subject],
                ["Classroom / Location", viewingEntry.room],
                ["Faculty", viewingEntry.faculty],
                ["Class", viewingEntry.classLabel],
                ["Department", viewingEntry.department],
                ["Academic Year", viewingEntry.academicYear],
                ["Semester", viewingEntry.semester],
                ["Subject Type", viewingEntry.subjectType],
                ["Session Type", viewingEntry.sessionType],
                ["Delivery Mode", viewingEntry.deliveryMode],
                ["Source Sheet", viewingEntry.sourceSheet],
                ["Source Cell", viewingEntry.sourceCellReference],
                ["Confidence", viewingEntry.confidenceLevel],
                ["Status", viewingEntry.status],
              ].filter(([, value]) => value && value !== "Not specified").map(([label, value]) => (
                <div key={label}><span>{label}</span><strong>{value}</strong></div>
              ))}
            </div>
            {Object.keys(viewingEntry.attributes || {}).length ? (
              <div className="entry-detail-attributes">
                <span>Additional data</span>
                <p>{Object.entries(viewingEntry.attributes).map(([key, value]) => `${key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join(", ") : value}`).join(" | ")}</p>
              </div>
            ) : null}
            <div className="form-actions">
              <Button onClick={() => setViewingEntry(null)} tone="secondary" type="button">Close</Button>
              <Button onClick={() => { const entry = viewingEntry; setViewingEntry(null); openEntryEditor(entry); }} type="button">
                <Pencil aria-hidden="true" size={15} /> Edit
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}

      {editingEntry && editForm ? (
        <Modal
          description={`${editingEntry.classLabel} | ${editingEntry.day} | ${editingEntry.time}`}
          onClose={closeEntryEditor}
          title="Edit timetable entry"
        >
          <form className="modal-form" onSubmit={handleEntryUpdate}>
            <div className="form-grid edit-entry-grid">
              <Field label="Subject / Activity" name="subject" onChange={handleEditChange} required value={editForm.subject} />
              <Field label="Faculty" name="facultyText" onChange={handleEditChange} value={editForm.facultyText} />
              <label className="field">
                <span>Classroom</span>
                <select name="roomHint" onChange={handleEditChange} value={editForm.roomHint}>
                  <option value="">No classroom</option>
                  {editForm.roomHint && !editableClassrooms.some((room) => room.room_number === editForm.roomHint) ? (
                    <option value={editForm.roomHint}>{editForm.roomHint}</option>
                  ) : null}
                  {editableClassrooms.map((room) => (
                    <option key={room.id} value={room.room_number}>
                      {room.room_number}{room.display_name ? ` | ${room.display_name}` : ""}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {editState.status === "error" ? <p className="field-error" role="alert">{editState.message}</p> : null}
            <div className="form-actions edit-entry-actions">
              <Button disabled={editState.status === "saving"} onClick={handleEntryDelete} tone="danger" type="button">
                <Trash2 aria-hidden="true" size={15} /> No activity
              </Button>
              <Button disabled={editState.status === "saving"} onClick={closeEntryEditor} tone="secondary" type="button">Cancel</Button>
              <Button disabled={editState.status === "saving"} type="submit">
                {editState.status === "saving" ? "Saving..." : "Save changes"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      <Section description={`${rows.length} database entries match the selected filters.`} title="Extracted Entries">
        <DataTable
          columns={[
            { key: "className", header: "Class" },
            { key: "division", header: "Division" },
            { key: "department", header: "Department" },
            { key: "day", header: "Day" },
            { key: "time", header: "Time" },
            { key: "subject", header: "Subject" },
            { key: "room", header: "Room / Location" },
            { key: "faculty", header: "Faculty" },
            ...attributeKeys.map((key) => ({
              key: `attribute-${key}`,
              header: key.replaceAll("_", " "),
              render: (row) => row.attributes?.[key] || "-",
            })),
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
          ]}
          emptyMessage="No timetable entries found for the selected filters."
          getRowKey={(row) => row.id}
          rows={rows}
        />
      </Section>
    </div>
  );
}

export function Allocation() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getAllocations);
  const [selectedRow, setSelectedRow] = useState(null);
  const [filters, setFilters] = useState({
    date: "2026-09-16",
    time: "All Times",
    department: "All Departments",
    building: "All Buildings",
    floor: "All Floors",
    room: "",
    status: "All Status",
  });

  const rows = data.filter((row) => {
    const dateMatch = row.date === filters.date;
    const timeMatch = filters.time === "All Times" || row.time === filters.time;
    const departmentMatch = filters.department === "All Departments" || row.department === filters.department;
    const buildingMatch = filters.building === "All Buildings" || row.building === filters.building;
    const floorMatch = filters.floor === "All Floors" || row.floor === filters.floor;
    const statusMatch = filters.status === "All Status" || row.status === filters.status;
    const roomMatch = row.room.toLowerCase().includes(filters.room.toLowerCase());
    return dateMatch && timeMatch && departmentMatch && buildingMatch && floorMatch && statusMatch && roomMatch;
  });

  const handleChange = (event) => setFilters({ ...filters, [event.target.name]: event.target.value });

  if (isLoading) return <LoadingState title="Loading allocations..." />;
  if (isError) return <ErrorState description={error} title="Unable to load allocations." />;

  return (
    <div className="page-stack">
      <PageHeader
        description="Review allocated, available, occupied, scheduled, and uncertain room states."
        eyebrow="Academic"
        title="Classroom Allocation"
      />

      <Toolbar>
        <Field label="Date" name="date" onChange={handleChange} type="date" value={filters.date} />
        <Field label="Time" name="time" onChange={handleChange} options={["All Times", ...data.map((row) => row.time)]} value={filters.time} />
        <Field label="Department" name="department" onChange={handleChange} options={["All Departments", ...departments]} value={filters.department} />
        <Field label="Building" name="building" onChange={handleChange} options={["All Buildings", "Main Building", "Science Block", "IT Block"]} value={filters.building} />
        <Field label="Floor" name="floor" onChange={handleChange} options={["All Floors", "1st Floor", "2nd Floor", "3rd Floor"]} value={filters.floor} />
        <Field label="Room" name="room" onChange={handleChange} placeholder="A-101" value={filters.room} />
        <Field label="Status" name="status" onChange={handleChange} options={["All Status", "Available", "Occupied", "Scheduled", "Uncertain"]} value={filters.status} />
      </Toolbar>

      <Section description="Click a row to inspect allocation details." title="Room Operations">
        <DataTable
          columns={[
            { key: "room", header: "Room" },
            { key: "time", header: "Time" },
            { key: "activity", header: "Activity" },
            { key: "department", header: "Department" },
            { key: "faculty", header: "Faculty" },
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
          ]}
          emptyMessage="No classroom allocations found for the selected filters."
          getRowKey={(row) => row.id}
          onRowClick={setSelectedRow}
          rows={rows}
        />
      </Section>

      {selectedRow ? (
        <Drawer description={`${selectedRow.date} | ${selectedRow.time}`} onClose={() => setSelectedRow(null)} title={`${selectedRow.room} allocation`}>
          <div className="detail-list">
            <span>Activity</span>
            <strong>{selectedRow.activity}</strong>
            <span>Department</span>
            <strong>{selectedRow.department}</strong>
            <span>Faculty</span>
            <strong>{selectedRow.faculty}</strong>
            <span>Location</span>
            <strong>
              {selectedRow.building}, {selectedRow.floor}
            </strong>
            <span>Capacity</span>
            <strong>{selectedRow.capacity} seats</strong>
            <span>Status</span>
            <StatusBadge value={selectedRow.status} />
          </div>
        </Drawer>
      ) : null}
    </div>
  );
}

export function Classrooms() {
  const { data, setData, isLoading, isError, error } = useResource(classOrbitApi.getClassrooms);
  const [search, setSearch] = useState("");
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [roomSchedule, setRoomSchedule] = useState([]);
  const [scheduleState, setScheduleState] = useState("idle");
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    room: "",
    capacity: "",
    name: "",
  });

  const rows = data.filter((room) => `${room.room} ${room.name}`.toLowerCase().includes(search.toLowerCase()));

  const handleFormChange = (event) => setFormData({ ...formData, [event.target.name]: event.target.value });
  const handleAdd = async (event) => {
    event.preventDefault();
    try {
      const created = await classOrbitApi.createClassroom({
        room_number: formData.room,
        display_name: formData.name || `Classroom ${formData.room}`,
        capacity: formData.capacity ? Number(formData.capacity) : null,
        facilities: [],
        status: "ACTIVE",
      });
      setData([...data, {
        id: created.id,
        room: created.room_number,
        name: created.display_name,
        type: "Classroom",
        capacity: created.capacity,
        facilities: created.facilities || [],
        status: "Active",
        lectureCount: 0,
      }].sort((left, right) => left.room.localeCompare(right.room)));
      setShowModal(false);
      setFormData({ room: "", capacity: "", name: "" });
    } catch (requestError) {
      setScheduleState(requestError.message);
    }
  };

  const openRoom = async (room) => {
    setSelectedRoom(room);
    setRoomSchedule([]);
    setScheduleState("loading");
    try {
      const schedule = await classOrbitApi.getRoomSchedule(room.room);
      const dayOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
      const dayIndex = (day) => {
        const index = dayOrder.indexOf(day);
        return index === -1 ? dayOrder.length : index;
      };
      setRoomSchedule(schedule
        .filter((entry) => entry.scheduled_status === "SCHEDULED")
        .sort((left, right) => (
          dayIndex(left.day) - dayIndex(right.day)
          || (left.start_time || "").localeCompare(right.start_time || "")
          || (left.subject || "").localeCompare(right.subject || "")
        )));
      setScheduleState("success");
    } catch (requestError) {
      setScheduleState(requestError.message);
    }
  };

  if (isLoading) return <LoadingState title="Loading classrooms..." />;
  if (isError) return <ErrorState description={error} title="Unable to load classrooms." />;

  return (
    <div className="page-stack">
      <PageHeader
        actions={<Button onClick={() => setShowModal(true)}>Add Classroom</Button>}
        description="Select a classroom to inspect every mapped lecture, event, and allocation."
        eyebrow="Academic"
        title="Classrooms"
      />

      <div className="stats-grid">
        <StatCard label="Total Rooms" value={data.length} />
        <StatCard label="Mapped Rooms" tone="success" value={data.filter((room) => room.lectureCount > 0).length} />
        <StatCard label="Mapped Lectures" value={data.reduce((total, room) => total + room.lectureCount, 0)} />
        <StatCard label="Unscheduled Rooms" tone="neutral" value={data.filter((room) => room.lectureCount === 0).length} />
      </div>

      <Toolbar>
        <SearchField onChange={(event) => setSearch(event.target.value)} placeholder="Search room name or number..." value={search} />
      </Toolbar>

      <Section description={`${rows.length} classrooms found. Blue rooms have mapped timetable activity.`} title="Classroom Map">
        <div className="classroom-tile-grid">
          {rows.map((room) => (
            <button
              className={room.lectureCount ? "classroom-tile scheduled" : "classroom-tile"}
              key={room.id}
              onClick={() => openRoom(room)}
              type="button"
            >
              <strong>{room.room}</strong>
              <span>{room.name}</span>
              <small>{room.lectureCount} mapped {room.lectureCount === 1 ? "lecture" : "lectures"}</small>
            </button>
          ))}
          {!rows.length ? <div className="timetable-empty">No classrooms match this search.</div> : null}
        </div>
      </Section>

      {selectedRoom ? (
        <Modal
          className="schedule-modal"
          description={`${selectedRoom.lectureCount} timetable mappings`}
          onClose={() => setSelectedRoom(null)}
          title={`${selectedRoom.room} | ${selectedRoom.name}`}
        >
          {scheduleState === "loading" ? <LoadingState title="Loading room schedule..." /> : null}
          {scheduleState !== "loading" && scheduleState !== "success" ? <ErrorState description={scheduleState} title="Unable to load room schedule." /> : null}
          {scheduleState === "success" ? (
            <DataTable
              columns={[
                { key: "day", header: "Day" },
                { key: "startLabel", header: "Start" },
                { key: "endLabel", header: "End" },
                { key: "subject", header: "Lecture / Event" },
                { key: "classLabel", header: "Class / Division" },
                { key: "faculty", header: "Faculty" },
                { key: "allocation_type", header: "Type" },
              ]}
              emptyMessage="No lectures or events are mapped to this classroom."
              getRowKey={(row) => `${row.source}-${row.day}-${row.start_time}-${row.subject}`}
              rows={roomSchedule}
            />
          ) : null}
        </Modal>
      ) : null}

      {showModal ? (
        <Modal description="Add a classroom to the live backend inventory." onClose={() => setShowModal(false)} title="Add Classroom">
          <form className="form-grid" onSubmit={handleAdd}>
            <Field label="Room Number" name="room" onChange={handleFormChange} placeholder="A-103" required value={formData.room} />
            <Field label="Display Name" name="name" onChange={handleFormChange} placeholder="Classroom A-103" value={formData.name} />
            <Field label="Capacity" min="1" name="capacity" onChange={handleFormChange} placeholder="60" type="number" value={formData.capacity} />
            <FormActions onCancel={() => setShowModal(false)} submitLabel="Add Classroom" />
          </form>
        </Modal>
      ) : null}
    </div>
  );
}

export function RoomRequests() {
  const { data, setData, isLoading, isError, error } = useResource(classOrbitApi.getRoomRequests);
  const [status, setStatus] = useState("All Status");
  const [selectedRequest, setSelectedRequest] = useState(null);
  const rows = status === "All Status" ? data : data.filter((request) => request.status === status);

  const updateStatus = (requestId, nextStatus) => {
    setData(data.map((request) => (request.id === requestId ? { ...request, status: nextStatus } : request)));
    setSelectedRequest((request) => (request ? { ...request, status: nextStatus } : request));
  };

  if (isLoading) return <LoadingState title="Loading room requests..." />;
  if (isError) return <ErrorState description={error} title="Unable to load room requests." />;

  return (
    <div className="page-stack">
      <PageHeader description="Review extra lecture, meeting, and academic-space requests from faculty." eyebrow="Requests" title="Room Requests" />
      <Toolbar>
        <Field label="Status" name="status" onChange={(event) => setStatus(event.target.value)} options={["All Status", "Pending", "Approved", "Rejected", "Cancelled"]} value={status} />
      </Toolbar>
      <Section description="Faculty can request rooms; only admins confirm allocation changes." title="Request Queue">
        <DataTable
          columns={[
            { key: "id", header: "Request ID" },
            { key: "requestedBy", header: "Requested By" },
            { key: "department", header: "Department" },
            { key: "purpose", header: "Purpose" },
            { key: "capacity", header: "Required Capacity" },
            { key: "date", header: "Date" },
            { key: "time", header: "Time" },
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
          ]}
          emptyMessage="No room requests found for the selected status."
          getRowKey={(row) => row.id}
          onRowClick={setSelectedRequest}
          rows={rows}
        />
      </Section>
      {selectedRequest ? (
        <Drawer description={`${selectedRequest.date} | ${selectedRequest.time}`} onClose={() => setSelectedRequest(null)} title={selectedRequest.id}>
          <div className="detail-list">
            <span>Faculty</span>
            <strong>{selectedRequest.requestedBy}</strong>
            <span>Purpose</span>
            <strong>{selectedRequest.purpose}</strong>
            <span>Number of students</span>
            <strong>{selectedRequest.students}</strong>
            <span>Required facilities</span>
            <strong>{selectedRequest.facilities.join(", ")}</strong>
            <span>Suggested classrooms</span>
            <strong>{selectedRequest.suggestedRooms.join(", ")}</strong>
            <span>Status</span>
            <StatusBadge value={selectedRequest.status} />
          </div>
          <div className="drawer-actions">
            <Button onClick={() => updateStatus(selectedRequest.id, "Approved")} size="sm">
              Approve
            </Button>
            <Button onClick={() => updateStatus(selectedRequest.id, "Rejected")} size="sm" tone="danger">
              Reject
            </Button>
          </div>
        </Drawer>
      ) : null}
    </div>
  );
}

export function Events() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getEvents);
  const [type, setType] = useState("All Types");
  const rows = type === "All Types" ? data : data.filter((event) => event.type === type);

  if (isLoading) return <LoadingState title="Loading events..." />;
  if (isError) return <ErrorState description={error} title="Unable to load events." />;

  return (
    <div className="page-stack">
      <PageHeader description="Prepare rooms for seminars, workshops, meetings, and academic events." eyebrow="Requests" title="Events" />
      <Toolbar>
        <Field label="Event Type" name="type" onChange={(event) => setType(event.target.value)} options={["All Types", "Seminar", "Workshop", "Meeting", "Academic Event", "Other"]} value={type} />
      </Toolbar>
      <Section description={`${rows.length} event records.`} title="Event Room Planning">
        <DataTable
          columns={[
            { key: "event", header: "Event" },
            { key: "department", header: "Department" },
            { key: "date", header: "Date" },
            { key: "time", header: "Time" },
            { key: "capacity", header: "Capacity" },
            { key: "requiredRoom", header: "Required Room" },
            { key: "allocationStatus", header: "Allocation Status", render: (row) => <StatusBadge value={row.allocationStatus} /> },
          ]}
          emptyMessage="No events found for the selected type."
          getRowKey={(row) => row.id}
          rows={rows}
        />
      </Section>
    </div>
  );
}

export function Examinations() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getExaminations);

  if (isLoading) return <LoadingState title="Loading examinations..." />;
  if (isError) return <ErrorState description={error} title="Unable to load examinations." />;

  return (
    <div className="page-stack">
      <PageHeader description="A lightweight planning module for examination room requirements." eyebrow="Requests" title="Examinations" />
      <Section description="Exam coordinator workflows can be added under /exam-coordinator later." title="Exam Room Planning">
        <DataTable
          columns={[
            { key: "examination", header: "Examination" },
            { key: "subject", header: "Subject" },
            { key: "date", header: "Date" },
            { key: "time", header: "Time" },
            { key: "studentCount", header: "Student Count" },
            { key: "requiredRooms", header: "Required Rooms" },
            { key: "allocationStatus", header: "Allocation Status", render: (row) => <StatusBadge value={row.allocationStatus} /> },
          ]}
          emptyMessage="No examination records found."
          getRowKey={(row) => row.id}
          rows={data}
        />
      </Section>
    </div>
  );
}

export function Occupancy() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getOccupancy);
  const [status, setStatus] = useState("All States");
  const rows = status === "All States" ? data : data.filter((record) => record.detectedStatus === status);

  if (isLoading) return <LoadingState title="Loading occupancy data..." />;
  if (isError) return <ErrorState description={error} title="Unable to load occupancy data." />;

  return (
    <div className="page-stack">
      <PageHeader
        description="Review live occupancy records when camera inference is connected."
        eyebrow="Intelligence"
        title="Occupancy"
      />
      <div className="stats-grid">
        <StatCard label="Available" tone="success" value={data.filter((record) => record.detectedStatus === "AVAILABLE").length} />
        <StatCard label="Occupied" tone="danger" value={data.filter((record) => record.detectedStatus === "OCCUPIED").length} />
        <StatCard label="Lecture" tone="info" value={data.filter((record) => record.detectedStatus === "LECTURE").length} />
        <StatCard label="Unknown" tone="neutral" value={data.filter((record) => record.detectedStatus === "UNKNOWN").length} />
      </div>
      <Toolbar>
        <Field label="Current State" name="status" onChange={(event) => setStatus(event.target.value)} options={["All States", "AVAILABLE", "OCCUPIED", "LECTURE", "UNKNOWN"]} value={status} />
      </Toolbar>
      <Section description="This view is ready for FastAPI occupancy responses." title="AI Occupancy Feed">
        <DataTable
          columns={[
            { key: "room", header: "Room" },
            { key: "detectedStatus", header: "Current State", render: (row) => <StatusBadge value={row.detectedStatus} /> },
            { key: "occupancyCount", header: "Approx. Occupancy", render: (row) => (row.occupancyCount === null ? "Unknown" : `${row.occupancyCount} students`) },
            { key: "confidence", header: "Confidence", render: (row) => `${Math.round(row.confidence * 100)}%` },
            { key: "detectedAt", header: "Last Updated", render: (row) => formatTime(row.detectedAt) },
          ]}
          emptyMessage="No occupancy records found for the selected state."
          getRowKey={(row) => row.id}
          rows={rows}
        />
      </Section>
    </div>
  );
}

export function Departments() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getDepartments);

  if (isLoading) return <LoadingState title="Loading departments..." />;
  if (isError) return <ErrorState description={error} title="Unable to load departments." />;

  return (
    <div className="page-stack">
      <PageHeader description="Maintain academic departments used across allocation, requests, and reporting." eyebrow="Management" title="Departments" />
      <Section description={`${data.length} active academic departments.`} title="Department Directory">
        <DataTable
          columns={[
            { key: "code", header: "Code" },
            { key: "name", header: "Department" },
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
          ]}
          emptyMessage="No departments found."
          getRowKey={(row) => row.id}
          rows={data}
        />
      </Section>
    </div>
  );
}

export function Faculty() {
  const { data, setData, isLoading, isError, error } = useResource(classOrbitApi.getFaculty);
  const { data: departmentRecords } = useResource(classOrbitApi.getDepartments);
  const [search, setSearch] = useState("");
  const [editingFaculty, setEditingFaculty] = useState(null);
  const [deletingFaculty, setDeletingFaculty] = useState(null);
  const [form, setForm] = useState({ name: "", email: "", employee_code: "", department_id: "" });
  const [formError, setFormError] = useState("");
  const rows = data.filter((member) => (
    `${member.name} ${member.email || ""} ${member.employee_code || ""} ${member.department}`
      .toLocaleLowerCase()
      .includes(search.toLocaleLowerCase())
  ));
  const openEditor = (member = null) => {
    setEditingFaculty(member || { id: null });
    setForm({
      name: member?.name || "",
      email: member?.email || "",
      employee_code: member?.employee_code || "",
      department_id: member?.department_id || "",
    });
    setFormError("");
  };
  const saveFaculty = async (event) => {
    event.preventDefault();
    const payload = {
      name: form.name.trim(),
      email: form.email.trim() || null,
      employee_code: form.employee_code.trim() || null,
      department_id: form.department_id || null,
    };
    try {
      if (editingFaculty.id) await classOrbitApi.updateFaculty(editingFaculty.id, payload);
      else await classOrbitApi.createFaculty(payload);
      setData(await classOrbitApi.getFaculty());
      setEditingFaculty(null);
    } catch (requestError) {
      setFormError(requestError.message);
    }
  };
  const removeFaculty = async () => {
    try {
      await classOrbitApi.deleteFaculty(deletingFaculty.id);
      setData(await classOrbitApi.getFaculty());
      setDeletingFaculty(null);
    } catch (requestError) {
      setFormError(requestError.message);
    }
  };

  if (isLoading) return <LoadingState title="Loading faculty..." />;
  if (isError) return <ErrorState description={error} title="Unable to load faculty." />;

  return (
    <div className="page-stack">
      <PageHeader
        actions={<Button onClick={() => openEditor()} type="button"><Plus aria-hidden="true" size={16} /> Add Faculty</Button>}
        description="Faculty extracted from timetable cells and maintained by administrators."
        eyebrow="Academic"
        title="Faculty"
      />
      <div className="stats-grid">
        <StatCard label="Faculty" value={data.length} detail="Unique faculty records" />
        <StatCard label="Mapped Lectures" value={data.reduce((total, member) => total + member.lectureCount, 0)} detail="Active timetable mappings" tone="info" />
        <StatCard label="Departments" value={new Set(data.map((member) => member.department).filter((value) => value !== "Not assigned")).size} detail="Represented departments" tone="success" />
      </div>
      <Toolbar><SearchField onChange={(event) => setSearch(event.target.value)} placeholder="Search faculty..." value={search} /></Toolbar>
      <Section description={`${rows.length} faculty records match the current search.`} title="Faculty Directory">
        <DataTable
          columns={[
            { key: "name", header: "Faculty Name" },
            { key: "employee_code", header: "Employee Code", render: (row) => row.employee_code || "-" },
            { key: "department", header: "Department" },
            { key: "email", header: "Email", render: (row) => row.email || "-" },
            { key: "subjectCount", header: "Subjects" },
            { key: "lectureCount", header: "Lectures" },
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              header: "Actions",
              render: (row) => (
                <div className="table-actions">
                  <button aria-label={`Edit ${row.name}`} className="icon-button" onClick={() => openEditor(row)} title="Edit faculty" type="button"><Pencil size={15} /></button>
                  <button aria-label={`Delete ${row.name}`} className="icon-button danger-icon" onClick={() => { setFormError(""); setDeletingFaculty(row); }} title="Delete faculty" type="button"><Trash2 size={15} /></button>
                </div>
              ),
            },
          ]}
          emptyMessage="No faculty records found."
          getRowKey={(row) => row.id}
          rows={rows}
        />
      </Section>
      {editingFaculty ? (
        <Modal description="Faculty details can also be populated automatically during timetable import." onClose={() => setEditingFaculty(null)} title={editingFaculty.id ? "Edit faculty" : "Add faculty"}>
          <form className="modal-form" onSubmit={saveFaculty}>
            <div className="form-grid edit-entry-grid">
              <Field label="Faculty Name" name="name" onChange={(event) => setForm({ ...form, name: event.target.value })} required value={form.name} />
              <Field label="Employee Code" name="employee_code" onChange={(event) => setForm({ ...form, employee_code: event.target.value })} value={form.employee_code} />
              <Field label="Email" name="email" onChange={(event) => setForm({ ...form, email: event.target.value })} type="email" value={form.email} />
              <label className="field">
                <span>Department</span>
                <select name="department_id" onChange={(event) => setForm({ ...form, department_id: event.target.value })} value={form.department_id}>
                  <option value="">Not assigned</option>
                  {departmentRecords.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}
                </select>
              </label>
            </div>
            {formError ? <p className="field-error" role="alert">{formError}</p> : null}
            <FormActions onCancel={() => setEditingFaculty(null)} submitLabel={editingFaculty.id ? "Save changes" : "Add faculty"} />
          </form>
        </Modal>
      ) : null}
      {deletingFaculty ? (
        <Modal description="Timetable text remains available, but the faculty mapping will be removed." onClose={() => setDeletingFaculty(null)} title="Delete faculty">
          <div className="confirmation-body">
            <strong>{deletingFaculty.name}</strong>
            {formError ? <p className="field-error" role="alert">{formError}</p> : null}
            <div className="form-actions">
              <Button onClick={() => setDeletingFaculty(null)} tone="secondary" type="button">Cancel</Button>
              <Button onClick={removeFaculty} tone="danger" type="button"><Trash2 aria-hidden="true" size={15} /> Delete faculty</Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

export function Subjects() {
  const { data, setData, isLoading, isError, error } = useResource(classOrbitApi.getSubjects);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("All Departments");
  const [editingSubject, setEditingSubject] = useState(null);
  const [deletingSubject, setDeletingSubject] = useState(null);
  const [subjectForm, setSubjectForm] = useState({ name: "", code: "" });
  const [subjectError, setSubjectError] = useState("");
  const departmentOptions = useMemo(
    () => [...new Set(data.flatMap((subject) => subject.departments).filter((name) => name !== "Not assigned"))].sort(),
    [data],
  );
  const rows = data.filter((subject) => {
    const searchMatch = `${subject.name} ${subject.code} ${subject.department} ${subject.teacherLabel}`.toLowerCase().includes(search.toLowerCase());
    const departmentMatch = department === "All Departments" || subject.departments.includes(department);
    return searchMatch && departmentMatch;
  });
  const openSubjectEditor = (subject) => {
    setEditingSubject(subject);
    setSubjectForm({ name: subject.name, code: subject.editableCode });
    setSubjectError("");
  };
  const saveSubject = async (event) => {
    event.preventDefault();
    try {
      const changes = {
        name: subjectForm.name,
      };
      if (editingSubject.codes.length <= 1 || subjectForm.code.trim()) {
        changes.code = subjectForm.code.trim() || null;
      }
      await classOrbitApi.updateSubjects(editingSubject.subjectIds, changes);
      setData(await classOrbitApi.getSubjects());
      setEditingSubject(null);
    } catch (requestError) {
      setSubjectError(requestError.message);
    }
  };
  const removeSubject = async (subject) => {
    try {
      await classOrbitApi.deleteSubjects(subject.subjectIds);
      setData(await classOrbitApi.getSubjects());
      if (editingSubject?.id === subject.id) setEditingSubject(null);
      setDeletingSubject(null);
    } catch (requestError) {
      setSubjectError(requestError.message);
    }
  };

  if (isLoading) return <LoadingState title="Loading subjects..." />;
  if (isError) return <ErrorState description={error} title="Unable to load subjects." />;

  return (
    <div className="page-stack">
      <PageHeader
        description="Review each unique subject with all mapped departments, assigned teachers, and active lecture usage."
        eyebrow="Academic"
        title="Subjects"
      />
      <div className="stats-grid">
        <StatCard label="Subjects" value={data.length} detail="Unique subject names" />
        <StatCard label="Departments" value={departmentOptions.length} detail="Represented in subjects" tone="info" />
        <StatCard label="With Teachers" value={data.filter((subject) => subject.teachers.length).length} detail="Faculty identified" tone="success" />
        <StatCard label="Active Lectures" value={data.reduce((total, subject) => total + subject.lectureCount, 0)} detail="Current timetable entries" />
      </div>
      <Toolbar>
        <SearchField onChange={(event) => setSearch(event.target.value)} placeholder="Search subject, code, or teacher..." value={search} />
        <Field label="Department" name="department" onChange={(event) => setDepartment(event.target.value)} options={["All Departments", ...departmentOptions]} value={department} />
      </Toolbar>
      <Section description={`${rows.length} unique subjects match the current filters.`} title="Subject Directory">
        <DataTable
          columns={[
            { key: "name", header: "Subject" },
            { key: "code", header: "Code" },
            { key: "department", header: "Department" },
            { key: "teacherLabel", header: "Taught By" },
            { key: "lectureCount", header: "Lectures" },
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              header: "Actions",
              render: (row) => (
                <div className="table-actions">
                  <button aria-label={`Edit ${row.name}`} className="icon-button" onClick={() => openSubjectEditor(row)} title="Edit subject" type="button"><Pencil size={15} /></button>
                  <button aria-label={`Delete ${row.name}`} className="icon-button danger-icon" onClick={() => setDeletingSubject(row)} title="Delete subject" type="button"><Trash2 size={15} /></button>
                </div>
              ),
            },
          ]}
          emptyMessage="No subjects match these filters."
          getRowKey={(row) => row.id}
          rows={rows}
        />
      </Section>
      {editingSubject ? (
        <Modal description={`${editingSubject.department} | ${editingSubject.lectureCount} mapped lectures. Changes apply to every listed department.`} onClose={() => setEditingSubject(null)} title="Edit subject">
          <form className="modal-form" onSubmit={saveSubject}>
            <div className="form-grid edit-entry-grid">
              <Field label="Subject Name" name="name" onChange={(event) => setSubjectForm({ ...subjectForm, name: event.target.value })} required value={subjectForm.name} />
              <Field label="Subject Code" name="code" onChange={(event) => setSubjectForm({ ...subjectForm, code: event.target.value })} value={subjectForm.code} />
            </div>
            {subjectError ? <p className="field-error" role="alert">{subjectError}</p> : null}
            <div className="form-actions edit-entry-actions">
              <Button onClick={() => { setDeletingSubject(editingSubject); setEditingSubject(null); }} tone="danger" type="button"><Trash2 aria-hidden="true" size={15} /> Delete</Button>
              <Button onClick={() => setEditingSubject(null)} tone="secondary" type="button">Cancel</Button>
              <Button type="submit">Save changes</Button>
            </div>
          </form>
        </Modal>
      ) : null}
      {deletingSubject ? (
        <Modal description="All department mappings for this subject will be removed. Existing timetable text remains intact." onClose={() => setDeletingSubject(null)} title="Delete subject">
          <div className="confirmation-body">
            <strong>{deletingSubject.name}</strong>
            {subjectError ? <p className="field-error" role="alert">{subjectError}</p> : null}
            <div className="form-actions">
              <Button onClick={() => setDeletingSubject(null)} tone="secondary" type="button">Cancel</Button>
              <Button onClick={() => removeSubject(deletingSubject)} tone="danger" type="button"><Trash2 aria-hidden="true" size={15} /> Delete subject</Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

export function TimeSlots() {
  const { data, isLoading, isError, error } = useResource(classOrbitApi.getTimeSlots);

  if (isLoading) return <LoadingState title="Loading time slots..." />;
  if (isError) return <ErrorState description={error} title="Unable to load time slots." />;

  const totalLectures = data.reduce((total, slot) => total + slot.lectureCount, 0);
  const busiest = data.reduce((current, slot) => (
    !current || slot.lectureCount > current.lectureCount ? slot : current
  ), null);

  return (
    <div className="page-stack">
      <PageHeader
        description="See each reusable timetable period and the number of active lectures scheduled within it."
        eyebrow="Academic"
        title="Time Slots"
      />
      <div className="stats-grid">
        <StatCard label="Time Slots" value={data.length} detail="Unique active periods" />
        <StatCard label="Scheduled Lectures" value={totalLectures} detail="Across active timetables" tone="info" />
        <StatCard label="Busiest Slot" value={busiest?.time || "None"} detail={busiest ? `${busiest.lectureCount} lectures` : "No lectures scheduled"} tone="warning" />
      </div>
      <Section description="Lecture totals update from active timetable entries." title="Slot Usage">
        <DataTable
          columns={[
            { key: "time", header: "Time Slot" },
            { key: "startLabel", header: "Starts" },
            { key: "endLabel", header: "Ends" },
            { key: "lectureCount", header: "Lectures" },
            { key: "subjectCount", header: "Subjects" },
            { key: "dayCount", header: "Days Used" },
          ]}
          emptyMessage="No active time slots were found."
          getRowKey={(row) => row.id}
          rows={data}
        />
      </Section>
    </div>
  );
}

export function Users() {
  const { data, setData, isLoading, isError, error } = useResource(classOrbitApi.getUsers);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("All Roles");
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    department: "Computer Science",
    role: "Faculty",
    status: "Invited",
    password: "",
  });

  const rows = data.filter((user) => {
    const searchMatch = `${user.name} ${user.email} ${user.department}`.toLowerCase().includes(search.toLowerCase());
    const roleMatch = role === "All Roles" || user.role === role;
    return searchMatch && roleMatch;
  });

  const handleChange = (event) => setFormData({ ...formData, [event.target.name]: event.target.value });
  const handleAdd = async (event) => {
    event.preventDefault();
    const roleMap = { Admin: "ADMIN", Faculty: "FACULTY", "Exam Coordinator": "EXAM_COORDINATOR" };
    try {
      const created = await classOrbitApi.createUser({
        name: formData.name,
        email: formData.email,
        password: formData.password,
        role: roleMap[formData.role],
      });
      setData([...data, {
        id: created.id,
        name: created.name,
        email: created.email,
        department: "Not assigned",
        role: formData.role,
        status: "Active",
      }]);
      setShowModal(false);
    } catch (requestError) {
      setFormData({ ...formData, status: requestError.message });
    }
  };

  if (isLoading) return <LoadingState title="Loading users..." />;
  if (isError) return <ErrorState description={error} title="Unable to load users." />;

  return (
    <div className="page-stack">
      <PageHeader
        actions={<Button onClick={() => setShowModal(true)}>Add User</Button>}
        description="Manage portal access for admins, faculty, and exam coordinators."
        eyebrow="Management"
        title="Users"
      />
      <Toolbar>
        <SearchField onChange={(event) => setSearch(event.target.value)} placeholder="Search users..." value={search} />
        <Field label="Role" name="role" onChange={(event) => setRole(event.target.value)} options={["All Roles", "Admin", "Faculty", "Exam Coordinator"]} value={role} />
      </Toolbar>
      <Section description={`${rows.length} users found.`} title="User Directory">
        <DataTable
          columns={[
            { key: "name", header: "Name" },
            { key: "email", header: "Email" },
            { key: "department", header: "Department" },
            { key: "role", header: "Role" },
            { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
          ]}
          emptyMessage="No users found for the selected filters."
          getRowKey={(row) => row.id}
          rows={rows}
        />
      </Section>
      {showModal ? (
        <Modal description="Create a frontend access record." onClose={() => setShowModal(false)} title="Add User">
          <form className="form-grid" onSubmit={handleAdd}>
            <Field label="Name" name="name" onChange={handleChange} placeholder="Dr. Neha Mehta" required value={formData.name} />
            <Field label="Email" name="email" onChange={handleChange} placeholder="name@college.edu" required type="email" value={formData.email} />
            <Field label="Temporary Password" name="password" onChange={handleChange} required type="password" value={formData.password} />
            <Field label="Department" name="department" onChange={handleChange} options={["Administration", ...departments, "Examination Cell"]} value={formData.department} />
            <Field label="Role" name="role" onChange={handleChange} options={["Admin", "Faculty", "Exam Coordinator"]} value={formData.role} />
            <Field label="Status" name="status" onChange={handleChange} options={["Active", "Invited", "Inactive"]} value={formData.status} />
            <FormActions onCancel={() => setShowModal(false)} submitLabel="Add User" />
          </form>
        </Modal>
      ) : null}
    </div>
  );
}

export function Settings() {
  const [settings, setSettings] = useState({
    institution: "ClassOrbit College",
    academicYear: "2026-2027",
    semester: "5th Semester",
    requestApproval: "Manual review",
    occupancySource: "Demo data",
    refreshInterval: "30 seconds",
  });
  const [message, setMessage] = useState("");

  const handleChange = (event) => {
    setSettings({ ...settings, [event.target.name]: event.target.value });
    setMessage("");
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setMessage("Settings saved locally for this prototype.");
  };

  return (
    <div className="page-stack">
      <PageHeader description="Configure the admin portal defaults used by the prototype." eyebrow="Management" title="Settings" />
      <form className="settings-form" onSubmit={handleSubmit}>
        <Section description="Academic context for allocation and timetable screens." title="Academic Setup">
          <div className="form-grid">
            <Field label="Institution Name" name="institution" onChange={handleChange} value={settings.institution} />
            <Field label="Academic Year" name="academicYear" onChange={handleChange} options={["2025-2026", "2026-2027", "2027-2028"]} value={settings.academicYear} />
            <Field label="Current Semester" name="semester" onChange={handleChange} options={semesters} value={settings.semester} />
          </div>
        </Section>
        <Section description="Backend-facing defaults for future integrations." title="System Preferences">
          <div className="form-grid">
            <Field label="Request Approval" name="requestApproval" onChange={handleChange} options={["Manual review", "Auto approve low-risk requests"]} value={settings.requestApproval} />
            <Field label="Occupancy Source" name="occupancySource" onChange={handleChange} options={["Demo data", "FastAPI occupancy endpoint"]} value={settings.occupancySource} />
            <Field label="Refresh Interval" name="refreshInterval" onChange={handleChange} options={["30 seconds", "1 minute", "5 minutes"]} value={settings.refreshInterval} />
          </div>
        </Section>
        {message ? <div className="success-message">{message}</div> : null}
        <div className="form-actions outside">
          <Button tone="secondary" type="button">
            Reset
          </Button>
          <Button type="submit">Save Changes</Button>
        </div>
      </form>
    </div>
  );
}

export function Profile() {
  const session = getSession();
  const [resetOpen, setResetOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [resetError, setResetError] = useState("");
  const [resetMessage, setResetMessage] = useState("");

  const closeReset = () => {
    if (isResetting) return;
    setResetOpen(false);
    setPassword("");
    setResetError("");
  };

  const handleReset = async (event) => {
    event.preventDefault();
    setIsResetting(true);
    setResetError("");
    setResetMessage("");
    try {
      const result = await classOrbitApi.resetTestData(password);
      setResetMessage(`${result.message} ${result.total_deleted} records removed.`);
      setResetOpen(false);
      setPassword("");
    } catch (error) {
      setResetError(error.message);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="page-stack">
      <PageHeader description="Admin identity and role information for the current session." eyebrow="Profile" title={session.user.name} />
      <Section title="Account">
        <div className="detail-list inline">
          <span>Email</span>
          <strong>{session.user.email}</strong>
          <span>Role</span>
          <strong>{session.user.role}</strong>
        </div>
      </Section>
      <Section
        className="danger-zone"
        description="Temporary testing control. This clears timetable, import, classroom, department, subject, faculty, allocation, building, and time-slot data. User accounts remain available."
        title="Delete test data"
      >
        <div className="danger-zone-action">
          <p>This action cannot be undone and requires your current admin password.</p>
          <Button onClick={() => { setResetMessage(""); setResetOpen(true); }} tone="danger" type="button">
            Delete all entries
          </Button>
        </div>
      </Section>
      {resetMessage ? <div className="success-message">{resetMessage}</div> : null}
      {resetOpen ? (
        <Modal
          description="All application data except user accounts and roles will be permanently deleted."
          onClose={closeReset}
          title="Confirm test data deletion"
        >
          <form className="modal-form" onSubmit={handleReset}>
            <Field
              label="Admin password"
              name="adminPassword"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            {resetError ? <p className="field-error" role="alert">{resetError}</p> : null}
            <div className="form-actions">
              <Button disabled={isResetting} onClick={closeReset} tone="secondary" type="button">
                Cancel
              </Button>
              <Button disabled={isResetting || !password} tone="danger" type="submit">
                {isResetting ? "Deleting..." : "Delete all entries"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}
