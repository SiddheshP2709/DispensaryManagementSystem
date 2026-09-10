# REST API Reference & Endpoint Specification

Base URL: `http://localhost:5000`

---

## 🔐 1. Authentication & Session APIs (`/api/auth`)

### Login
- **Endpoint**: `POST /login` (or `/api/auth/login`)
- **Access**: Public
- **Request Body**:
  ```json
  {
    "user": "doctor1",
    "password": "password123"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "member_id": 5,
    "role": "Doctor",
    "name": "Dr. Sarah Smith"
  }
  ```

### Verify Token / Session
- **Endpoint**: `GET /isAuth`
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**: Returns verified claims and permissions.

### Audit Logs
- **Endpoint**: `GET /audit_logs`
- **Access**: Admin only
- **Response (200 OK)**: Returns list of system audit actions with timestamps and username metadata.

---

## 👤 2. Member & User Portfolio APIs (`/api/member`)

### Get Member Portfolio
- **Endpoint**: `GET /portfolio/<member_id>`
- **Access**: Admin, Doctor, or Self (Patient)
- **Routing**: Automatically routed to the target shard via `MD5(member_id) % 3`
- **Response (200 OK)**:
  ```json
  {
    "member_id": 7,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "9876543210",
    "role": "Patient"
  }
  ```

---

## 👨‍⚕️ 3. Doctor Management APIs (`/api/doctor`)

### List All Doctors
- **Endpoint**: `GET /doctors`
- **Access**: Public / Authenticated
- **Routing**: Multi-shard Scatter-Gather query aggregated across Shards 0, 1, and 2.
- **Response (200 OK)**: Returns list of available doctors with specializations and department information.

---

## 🏥 4. Patient Management APIs (`/api/patient`)

### Get Patient Appointments
- **Endpoint**: `GET /my_appointments`
- **Access**: Patient (Self)
- **Routing**: Routed to patient's assigned shard.
- **Response (200 OK)**: Returns list of upcoming and past consultations.

---

## 📅 5. Appointment Scheduling APIs (`/api/appointment`)

### List Appointments
- **Endpoint**: `GET /appointments`
- **Access**: Admin / Staff / Doctor
- **Routing**: Broadcast query aggregated across all active shards.

### Schedule New Appointment
- **Endpoint**: `POST /add_appointment`
- **Access**: Patient / Admin
- **Request Body**:
  ```json
  {
    "patient_member_id": 5,
    "doctor_id": 2,
    "appointment_date": "2026-04-20",
    "slot_id": 3
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "message": "Appointment booked successfully",
    "appointment_id": 104,
    "shard_id": 2
  }
  ```
- **Error (409 Conflict)**: Returned if the doctor or patient is already booked for that specific time slot.

---

## 💊 6. Pharmacy & Inventory APIs (`/api/medicine`)

### List Medicines
- **Endpoint**: `GET /medicines`
- **Access**: Public / Authenticated
- **Response (200 OK)**: Replicated catalog returned from local/shard cache.

### Add / Update Inventory Stock
- **Endpoint**: `POST /add_medicine` | `PUT /update_medicine/<id>`
- **Access**: Admin / Pharmacist
- **Request Body**:
  ```json
  {
    "name": "Paracetamol 500mg",
    "manufacturer": "Cipla",
    "unit_price": 2.50,
    "stock_quantity": 500,
    "expiry_date": "2028-12-31"
  }
  ```

---

## 🛠️ 7. Administrator APIs (`/api/admin`)

### Register New Member
- **Endpoint**: `POST /add_member`
- **Access**: Admin only
- **Process**: Performs atomic multi-step insertion into authentication tables and routes patient/doctor records to the designated shard.

### Delete Member
- **Endpoint**: `DELETE /member/<id>`
- **Access**: Admin only
- **Process**: Cascades deletion across authentication and sharded record tables.
