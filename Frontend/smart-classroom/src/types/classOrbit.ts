export type Role = "Admin" | "Faculty" | "Exam Coordinator" | "Super Admin";

export type Department = {
  id: string;
  name: string;
  code: string;
  head: string;
  classrooms: number;
  faculty: number;
  status: "Active" | "Inactive";
};

export type ClassroomStatus =
  | "Available"
  | "Occupied"
  | "Scheduled"
  | "Uncertain"
  | "Maintenance";

export type Classroom = {
  id: string;
  room: string;
  building: string;
  floor: string;
  type: string;
  capacity: number;
  department: string;
  facilities: string[];
  status: ClassroomStatus;
};

export type TimetableEntry = {
  id: string;
  className: string;
  day: string;
  time: string;
  room: string;
  subject: string;
  faculty: string;
  department: string;
  academicYear: string;
  semester: string;
  status: "Scheduled" | "Draft" | "Cancelled";
};

export type Allocation = {
  id: string;
  room: string;
  time: string;
  activity: string;
  department: string;
  faculty: string;
  status: "Allocated" | "Available" | "Occupied" | "Scheduled" | "Uncertain";
  building: string;
  floor: string;
  date: string;
  capacity: number;
};

export type RoomRequestStatus = "Pending" | "Approved" | "Rejected" | "Cancelled";

export type RoomRequest = {
  id: string;
  requestedBy: string;
  department: string;
  purpose: string;
  capacity: number;
  date: string;
  time: string;
  status: RoomRequestStatus;
  facilities: string[];
  students: number;
  suggestedRooms: string[];
};

export type CollegeEvent = {
  id: string;
  event: string;
  type: "Seminar" | "Workshop" | "Meeting" | "Academic Event" | "Other";
  department: string;
  date: string;
  time: string;
  capacity: number;
  requiredRoom: string;
  allocationStatus: string;
};

export type Examination = {
  id: string;
  examination: string;
  subject: string;
  date: string;
  time: string;
  studentCount: number;
  requiredRooms: number;
  allocationStatus: string;
};

export type OccupancyRecord = {
  id: string;
  classroomId: string;
  room: string;
  detectedStatus: "AVAILABLE" | "OCCUPIED" | "LECTURE" | "UNKNOWN";
  occupancyCount: number | null;
  confidence: number;
  detectedAt: string;
  source: "Sample" | "Api";
};

export type User = {
  id: string;
  name: string;
  email: string;
  department: string;
  role: Role;
  status: "Active" | "Invited" | "Inactive";
};
