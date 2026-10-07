# ClassOrbit

### AI-Based Classroom Occupancy & Smart Room Allocation System

ClassOrbit is an intelligent classroom management system designed for educational institutions to simplify timetable management, classroom allocation, room availability tracking, and classroom utilization.

The system aims to reduce the manual effort involved in finding available classrooms for extra lectures, events, examinations, and other academic activities.

The project combines centralized timetable and classroom management with a planned AI-based classroom occupancy detection module.

---

## 🎯 Project Overview

In many educational institutions, classroom allocation and availability management are handled manually using spreadsheets, documents, timetables, and communication between departments.

This makes it difficult to quickly determine:

- Which classroom is currently scheduled?
- Which classroom is available according to the timetable?
- Which room can be assigned for an extra lecture?
- Which classroom is allocated to a particular class?
- Which rooms are suitable for an examination or event?
- How does the scheduled classroom status compare with actual occupancy?

ClassOrbit is being developed to provide a centralized platform for managing and analyzing this information.

---

## 🚨 Problem Statement

Educational institutions often manage classroom timetables and room allocations manually.

When a faculty member or department requires a classroom for an extra lecture, event, examination, or other academic activity, staff may need to manually check multiple timetables, files, and existing allocations.

This process can be time-consuming, difficult to maintain, and prone to human error.

Additionally, scheduled classroom information does not necessarily represent the actual physical occupancy of a classroom.

ClassOrbit aims to address these problems through centralized timetable management, classroom allocation, availability analysis, and future AI-based occupancy detection.

---

## 🎯 Objectives

- Centralize classroom and timetable information.
- Digitize classroom allocation management.
- Reduce manual effort in finding available classrooms.
- Provide quick classroom availability information.
- Support extra lecture and event room allocation.
- Support examination classroom allocation.
- Provide role-based access to classroom information.
- Automatically extract timetable information from supported files.
- Map timetable entries with classroom master data.
- Provide intelligent room recommendations.
- Extend the system with AI-based classroom occupancy detection.

---

## ✨ Key Features

### Timetable Management

- Upload timetable files.
- Import standardized ClassOrbit timetable templates.
- Support existing timetable files.
- Extract timetable information.
- Normalize timetable data.
- Validate extracted records.
- Review ambiguous records before importing.

### Classroom Management

- Manage classroom information.
- Store classroom capacity.
- Store building and floor information.
- Store classroom type.
- Store available facilities.
- Map timetable entries to classrooms.

### Smart Room Availability

- Search classrooms by date and time.
- Identify classrooms available according to the scheduled timetable.
- Check classroom capacity and requirements.
- Support extra lecture and event requirements.

### Classroom Allocation

- Allocate classrooms to academic activities.
- Manage scheduled classroom assignments.
- Detect allocation conflicts.
- Provide suitable classroom recommendations.

### Role-Based Access

The system is designed around role-based access.

#### Administrator

- Manage timetable
- Manage classrooms
- Manage departments
- Manage subjects
- Manage faculty
- Manage allocations
- Review imported data

#### Faculty

- View timetable
- Search classroom information
- Check scheduled availability

#### Examination Coordinator

- Manage examination-related classroom allocation
- View classroom availability

---

## 🤖 AI-Based Classroom Occupancy

A future module of ClassOrbit will use computer vision to analyze classroom camera/video input.

The planned pipeline is:

Camera / Video
↓
Computer Vision
↓
Occupancy Detection
↓
Classroom State
↓
ClassOrbit Backend
↓
Occupancy Information

The system may identify classroom states such as:

- Vacant
- Occupied
- Lecture / Activity
- Unknown

This information can later be compared with the scheduled timetable.

For example:

Scheduled:

Room 204
09:00–10:00
DBMS

AI Detection:

Room 204
Currently Vacant

The system can identify a possible difference between scheduled and actual classroom usage.

> **Note:** The AI occupancy module is planned as a future development phase.

---

## 📊 Timetable Data Processing

ClassOrbit uses two approaches for timetable data.

### Standard ClassOrbit Template

The recommended method is the official ClassOrbit timetable template.

The template provides a consistent structure that allows the system to reliably identify:

- Department
- Program
- Class
- Division
- Semester
- Day
- Time slot
- Subject
- Faculty
- Classroom
- Activity type

### Existing Timetable Files

ClassOrbit also aims to support existing institutional files such as:

- Excel
- CSV
- PDF
- DOCX

The processing pipeline is:

File Upload
↓
File Analysis
↓
Data Extraction
↓
Normalization
↓
Validation
↓
Classroom / Master Data Mapping
↓
Review
↓
Database Storage

The original source information is preserved for traceability.

---

## 🏗️ System Architecture

```text
                    ClassOrbit
                        │
        ┌───────────────┴───────────────┐
        │                               │
     Frontend                         Backend
        │                               │
        │                         FastAPI APIs
        │                               │
        │                    ┌──────────┴──────────┐
        │                    │                     │
        │               Timetable             Classroom
        │               Processing            Management
        │                    │                     │
        │                    └──────────┬──────────┘
        │                               │
        │                          PostgreSQL
        │                               │
        └───────────────────────────────┘

                         Future AI Module
                                │
                              CCTV
                                ↓
                         Computer Vision
                                ↓
                        Occupancy Detection
```
