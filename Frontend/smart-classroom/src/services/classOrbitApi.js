import { getSession, normalizeBackendUser } from "../auth/session";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

function formatClockTime(value) {
  const match = /^(\d{1,2}):(\d{2})/.exec(value || "");
  if (!match) return value || "";
  const hour = Number(match[1]);
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${match[2]} ${hour < 12 ? "AM" : "PM"}`;
}

const formatTimeRange = (start, end) => `${formatClockTime(start)} - ${formatClockTime(end)}`;

function timetableLabel(timetable) {
  const values = [];
  const add = (value) => {
    const text = String(value || "").trim();
    if (text && !values.some((item) => item.toLowerCase() === text.toLowerCase())) values.push(text);
  };
  add(timetable.class_name || "Unknown class");
  if (timetable.division) add(`Div ${timetable.division}`);
  return values.join(" - ");
}

function timetableClassKey(timetable) {
  return [timetable.class_name || "Unknown class", timetable.division || ""]
    .map((value) => String(value).trim().toLocaleLowerCase())
    .join("::");
}

async function apiRequest(path, options = {}) {
  const session = getSession();
  const headers = new Headers(options.headers || {});
  if (session?.accessToken) headers.set("Authorization", `Bearer ${session.accessToken}`);
  if (options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `Request failed (${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}

async function downloadApiFile(path, filename) {
  const session = getSession();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {},
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Unable to download the timetable template.");
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function loginWithBackend(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const token = await apiRequest("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token.access_token}` },
  });
  if (!response.ok) throw new Error("Unable to load your account.");
  return { user: normalizeBackendUser(await response.json()), accessToken: token.access_token };
}

export async function registerWithBackend(payload) {
  const response = await apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return {
    user: normalizeBackendUser(response.user),
    accessToken: response.token.access_token,
  };
}

const quickActions = [
  { label: "View Timetable", to: "/admin/timetable" },
  { label: "View Classrooms", to: "/admin/classrooms" },
  { label: "View Allocations", to: "/admin/allocation" },
];

function mapTimetableEntry(entry, timetable, department) {
  const division = timetable.division || "";
  const programName = timetable.program_name || "";
  return {
    id: entry.id,
    timetableId: entry.timetable_id,
    classKey: timetableClassKey(timetable),
    className: timetable.class_name || "Unknown",
    division,
    classLabel: timetableLabel(timetable),
    department,
    programName,
    day: entry.day_of_week,
    startTime: entry.start_time,
    endTime: entry.end_time,
    time: formatTimeRange(entry.start_time, entry.end_time),
    timeSlotId: entry.time_slot_id,
    room: entry.room_hint || (entry.location_type === "ONLINE" ? "Online" : entry.location_type === "DEPARTMENT" ? department : "Not assigned"),
    roomHint: entry.room_hint || "",
    subject: entry.subject_text,
    subjectType: entry.subject_type,
    sessionType: entry.session_type,
    deliveryMode: entry.delivery_mode,
    faculty: entry.faculty_text || "Not specified",
    facultyText: entry.faculty_text || "",
    academicYear: timetable.academic_year || "Not specified",
    semester: timetable.semester || "Not specified",
    status: entry.validation_status === "VALID" ? "Scheduled" : "Needs Review",
    validationStatus: entry.validation_status,
    mappingStatus: entry.mapping_status,
    sourcePage: entry.source_page,
    sourceSheet: entry.source_sheet,
    sourceRow: entry.source_row,
    sourceColumn: entry.source_column,
    sourceCellReference: entry.source_cell_reference,
    rawCellText: entry.raw_cell_text,
    rawEntryText: entry.raw_entry_text,
    extractionMethod: entry.extraction_method,
    confidenceLevel: entry.confidence_level,
    attributes: entry.attributes_json || {},
  };
}

export const classOrbitApi = {
  getClassrooms: async () => {
    const [rooms, entries, buildings, floors, roomTypes, departments] = await Promise.all([
      apiRequest("/classrooms"),
      apiRequest("/timetable-entries"),
      apiRequest("/buildings"),
      apiRequest("/floors"),
      apiRequest("/room-types"),
      apiRequest("/departments"),
    ]);
    const buildingById = new Map(buildings.map((item) => [item.id, item.name]));
    const floorById = new Map(floors.map((item) => [item.id, item.name]));
    const roomTypeById = new Map(roomTypes.map((item) => [item.id, item.name]));
    const departmentById = new Map(departments.map((item) => [item.id, item.name]));
    const lectureCounts = entries.reduce((counts, entry) => {
      if (entry.classroom_id) counts.set(entry.classroom_id, (counts.get(entry.classroom_id) || 0) + 1);
      return counts;
    }, new Map());
    return rooms.map((room) => ({
      id: room.id,
      room: room.room_number,
      name: room.display_name || `Classroom ${room.room_number}`,
      building: buildingById.get(room.building_id) || "Building not assigned",
      floor: floorById.get(room.floor_id) || "Floor not assigned",
      type: roomTypeById.get(room.room_type_id) || "Classroom",
      department: departmentById.get(room.department_id) || "Not assigned",
      capacity: room.capacity,
      facilities: room.facilities || [],
      status: room.status === "ACTIVE" ? "Active" : room.status,
      lectureCount: lectureCounts.get(room.id) || 0,
    }));
  },
  getTimetableStructures: async () => {
    const [structures, departments] = await Promise.all([
      apiRequest("/timetable-structures"),
      apiRequest("/departments"),
    ]);
    const departmentById = new Map(departments.map((item) => [item.id, item]));
    return structures.map((structure) => {
      const timetable = structure.timetable;
      const department = departmentById.get(timetable.department_id)?.name || "Not specified";
      return {
        id: timetable.id,
        classKey: timetableClassKey(timetable),
        className: timetable.class_name || "Unknown class",
        division: timetable.division || "",
        classLabel: timetableLabel(timetable),
        department,
        academicYear: timetable.academic_year || "Not specified",
        metadata: timetable.metadata_json || {},
        columns: structure.columns || [],
        timeSlots: (structure.time_slots || []).map((slot) => ({
          id: slot.id,
          startTime: slot.start_time,
          endTime: slot.end_time,
          time: formatTimeRange(slot.start_time, slot.end_time),
        })),
        attributeKeys: structure.attribute_keys || [],
        entries: structure.entries.map((entry) => mapTimetableEntry(entry, timetable, department)),
      };
    });
  },
  getTimetable: async () => (await classOrbitApi.getTimetableStructures()).flatMap((structure) => structure.entries),
  getAllocations: async () => {
    const [allocations, rooms] = await Promise.all([apiRequest("/allocations"), apiRequest("/classrooms")]);
    const roomById = new Map(rooms.map((room) => [room.id, room]));
    return allocations.map((allocation) => ({
      id: allocation.id,
      room: roomById.get(allocation.classroom_id)?.room_number || "Unknown",
      time: formatTimeRange(allocation.start_time, allocation.end_time),
      activity: allocation.title,
      department: "Not specified",
      faculty: allocation.faculty_text || "Not specified",
      status: allocation.status,
      building: "Not assigned",
      floor: "Not assigned",
      date: allocation.allocation_date,
      capacity: roomById.get(allocation.classroom_id)?.capacity,
    }));
  },
  getRoomRequests: () => Promise.resolve([]),
  getEvents: () => Promise.resolve([]),
  getExaminations: () => Promise.resolve([]),
  getOccupancy: () => Promise.resolve([]),
  getDepartments: () => apiRequest("/departments"),
  getFaculty: async () => {
    const [faculty, departments, entries] = await Promise.all([
      apiRequest("/faculty"),
      apiRequest("/departments"),
      apiRequest("/timetable-entries"),
    ]);
    const departmentById = new Map(departments.map((item) => [item.id, item.name]));
    return faculty.map((member) => {
      const lectures = entries.filter((entry) => (
        entry.faculty_id === member.id
        || (!entry.faculty_id && entry.faculty_text?.toLocaleLowerCase() === member.name.toLocaleLowerCase())
      ));
      return {
        ...member,
        department: departmentById.get(member.department_id) || "Not assigned",
        lectureCount: lectures.length,
        subjectCount: new Set(lectures.map((entry) => entry.subject_id || entry.subject_text)).size,
      };
    }).sort((left, right) => left.name.localeCompare(right.name));
  },
  getSubjects: async () => {
    const [subjects, departments, faculty, entries] = await Promise.all([
      apiRequest("/subjects"),
      apiRequest("/departments"),
      apiRequest("/faculty"),
      apiRequest("/timetable-entries"),
    ]);
    const departmentById = new Map(departments.map((item) => [item.id, item.name]));
    const facultyById = new Map(faculty.map((item) => [item.id, item.name]));
    const grouped = new Map();
    subjects.forEach((subject) => {
      const lectures = entries.filter((entry) => entry.subject_id === subject.id);
      const teachers = [...new Set(lectures.map((entry) => (
        entry.faculty_id ? facultyById.get(entry.faculty_id) : entry.faculty_text
      )).filter(Boolean))].sort();
      const key = subject.name.trim().replace(/\s+/g, " ").toLocaleLowerCase();
      const current = grouped.get(key) || {
        id: subject.id,
        subjectIds: [],
        name: subject.name.trim().replace(/\s+/g, " "),
        codes: [],
        departments: [],
        teachers: [],
        lectureCount: 0,
        statuses: [],
      };
      current.subjectIds.push(subject.id);
      if (subject.code && !current.codes.includes(subject.code)) current.codes.push(subject.code);
      const departmentName = departmentById.get(subject.department_id) || "Not assigned";
      if (!current.departments.includes(departmentName)) current.departments.push(departmentName);
      teachers.forEach((teacher) => {
        if (!current.teachers.includes(teacher)) current.teachers.push(teacher);
      });
      current.lectureCount += lectures.length;
      current.statuses.push(subject.status);
      grouped.set(key, current);
    });
    return [...grouped.values()].map((subject) => ({
      ...subject,
      codes: subject.codes.sort(),
      code: subject.codes.length ? subject.codes.sort().join(", ") : "Not assigned",
      editableCode: subject.codes.length === 1 ? subject.codes[0] : "",
      departments: subject.departments.sort(),
      department: subject.departments.sort().join(", "),
      teachers: subject.teachers.sort(),
      teacherLabel: subject.teachers.length ? subject.teachers.sort().join(", ") : "Not assigned",
      status: subject.statuses.every((status) => status === "ACTIVE") ? "ACTIVE" : "MIXED",
    })).sort((left, right) => left.name.localeCompare(right.name));
  },
  getTimeSlots: async () => {
    const [slots, entries] = await Promise.all([
      apiRequest("/time-slots"),
      apiRequest("/timetable-entries"),
    ]);
    return slots.map((slot) => {
      const lectures = entries.filter((entry) => entry.time_slot_id === slot.id);
      return {
        id: slot.id,
        startTime: slot.start_time,
        endTime: slot.end_time,
        time: formatTimeRange(slot.start_time, slot.end_time),
        startLabel: formatClockTime(slot.start_time),
        endLabel: formatClockTime(slot.end_time),
        lectureCount: lectures.length,
        subjectCount: new Set(lectures.map((entry) => entry.subject_id).filter(Boolean)).size,
        dayCount: new Set(lectures.map((entry) => entry.day_of_week)).size,
      };
    });
  },
  getUsers: async () => (await apiRequest("/users")).map((user) => ({
    id: user.id,
    name: user.name,
    email: user.email,
    department: user.department_id || "Not assigned",
    role: user.role?.name === "EXAM_COORDINATOR" ? "Exam Coordinator" : `${user.role?.name?.charAt(0) || ""}${user.role?.name?.slice(1).toLowerCase()}`,
    status: `${user.status.charAt(0)}${user.status.slice(1).toLowerCase()}`,
  })),
  createUser: (payload) => apiRequest("/users", { method: "POST", body: JSON.stringify(payload) }),
  createFaculty: (payload) => apiRequest("/faculty", { method: "POST", body: JSON.stringify(payload) }),
  updateFaculty: (facultyId, payload) => apiRequest(`/faculty/${facultyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  deleteFaculty: (facultyId) => apiRequest(`/faculty/${facultyId}`, { method: "DELETE" }),
  updateSubject: (subjectId, payload) => apiRequest(`/subjects/${subjectId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  updateSubjects: (subjectIds, payload) => Promise.all(
    subjectIds.map((subjectId) => classOrbitApi.updateSubject(subjectId, payload)),
  ),
  deleteSubject: (subjectId) => apiRequest(`/subjects/${subjectId}`, { method: "DELETE" }),
  deleteSubjects: (subjectIds) => Promise.all(
    subjectIds.map((subjectId) => classOrbitApi.deleteSubject(subjectId)),
  ),
  resetTestData: (password) => apiRequest("/admin/test-data/reset", {
    method: "POST",
    body: JSON.stringify({ password }),
  }),
  getQuickActions: () => Promise.resolve(quickActions),
  getAdminOverview: async () => {
    const [classrooms, allocations, timetable] = await Promise.all([
      classOrbitApi.getClassrooms(),
      classOrbitApi.getAllocations(),
      classOrbitApi.getTimetable(),
    ]);
    return { classrooms, allocations, requests: [], timetable, quickActions };
  },
  getBackendTimetable: () => apiRequest("/timetable-entries"),
  getBackendTimetables: () => apiRequest("/timetables"),
  getBackendClassrooms: () => apiRequest("/classrooms"),
  downloadTimetableTemplate: () => downloadApiFile(
    "/timetables/template/download",
    "ClassOrbit_Timetable_Template.xlsx",
  ),
  getImport: (importId) => apiRequest(`/imports/${importId}`),
  getImportReviews: (importId) => apiRequest(`/imports/${importId}/review`),
  updateImportReview: (importId, reviewId, payload) => apiRequest(`/imports/${importId}/review/${reviewId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  confirmImport: (importId) => apiRequest(`/imports/${importId}/confirm`, { method: "POST" }),
  createTimeSlot: (payload) => apiRequest("/time-slots", { method: "POST", body: JSON.stringify(payload) }),
  createTimetableEntry: (payload) => apiRequest("/timetable-entries", { method: "POST", body: JSON.stringify(payload) }),
  updateTimetableEntry: (entryId, payload) => apiRequest(`/timetable-entries/${entryId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  deleteTimetableEntry: (entryId) => apiRequest(`/timetable-entries/${entryId}`, { method: "DELETE" }),
  createClassroom: (payload) => apiRequest("/classrooms", { method: "POST", body: JSON.stringify(payload) }),
  getRoomSchedule: async (room) => (await apiRequest(`/schedule/by-room?${new URLSearchParams({ room })}`)).map((entry) => ({
    ...entry,
    classLabel: [entry.class_name, entry.division].filter(Boolean).join(" - ") || "Not specified",
    startLabel: formatClockTime(entry.start_time),
    endLabel: formatClockTime(entry.end_time),
  })),
  getNotifications: async () => {
    const imports = await apiRequest("/imports");
    return imports.slice(0, 12).map((item) => ({
      id: item.id,
      title: item.status === "FAILED" ? "Timetable import failed" : "Timetable import processed",
      message: item.status === "FAILED"
        ? item.error_message || item.original_filename
        : `${item.summary_json?.generated_timetable_entries || 0} entries${item.summary_json?.departments?.length ? ` across ${item.summary_json.departments.length} departments` : ""} extracted from ${item.original_filename}`,
      status: item.status,
      createdAt: item.created_at,
    }));
  },
  getAvailability: ({ room, day, startTime, endTime }) => {
    const params = new URLSearchParams({ room, day, start_time: startTime, end_time: endTime });
    return apiRequest(`/availability?${params}`);
  },
  uploadTimetable: (file, onProgress, { standard = false } = {}) => new Promise((resolve, reject) => {
    const session = getSession();
    const request = new XMLHttpRequest();
    const body = new FormData();
    body.append("file", file);
    request.open("POST", `${API_BASE_URL}/imports${standard ? "/standard" : ""}`);
    if (session?.accessToken) request.setRequestHeader("Authorization", `Bearer ${session.accessToken}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onload = () => {
      let payload;
      try {
        payload = JSON.parse(request.responseText);
      } catch {
        payload = null;
      }
      if (request.status >= 200 && request.status < 300) resolve(payload);
      else reject(new Error(payload?.detail || `Upload failed (${request.status}).`));
    };
    request.onerror = () => reject(new Error("Unable to reach the ClassOrbit backend."));
    request.send(body);
  }),
};
