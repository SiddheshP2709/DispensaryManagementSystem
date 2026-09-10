# REST API Reference and Endpoint Specification

Base URL: `http://localhost:5000`

---

## 1. Authentication and Session Endpoints (`/api/auth`)

### Login
- **Endpoint**: `POST /login` (or `/api/auth/login`)
- **Access**: Public
- **Request Body**:
  ```json
  {
    "user": "doctor1",
    "password": "Doctor1pass"
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

### Verify Session / Token
- **Endpoint**: `GET /isAuth`
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**: Returns verified claims and permissions.

### Audit Logs
- **Endpoint**: `GET /audit_logs`
- **Access**: Admin only
- **Response (200 OK)**: Returns list of recorded audit actions with timestamps and user details.

---

## 2. Member Endpoints (`/api/member`)

### Get Member Portfolio
- **Endpoint**: `GET /portfolio/<member_id>`
- **Access**: Admin, Doctor, or Self (Patient)
- **Routing**: Routed to target shard via `MD5(member_id) % 3`
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

## 3. Doctor Management Endpoints (`/api/doctor`)

### List All Doctors
- **Endpoint**: `GET /doctors`
- **Access**: Public / Authenticated
- **Routing**: Scatter-gather query aggregated across Shards 0, 1, and 2.
- **Response (200 OK)**: Returns array of doctors with departmental details.

---

## 4. Patient Management Endpoints (`/api/patient`)

### Get Patient Appointments
- **Endpoint**: `GET /my_appointments`
- **Access**: Patient (Self)
- **Routing**: Routed to the patient's assigned shard.
- **Response (200 OK)**: Returns list of appointments.

---

## 5. Appointment Scheduling Endpoints (`/api/appointment`)

### List Appointments
- **Endpoint**: `GET /appointments`
- **Access**: Admin / Staff / Doctor
- **Routing**: Aggregated across active shards.

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
- **Response (409 Conflict)**: Returned if the doctor or slot is already booked.

---

## 6. Pharmacy and Inventory Endpoints (`/api/medicine`)

### List Medicines
- **Endpoint**: `GET /medicines`
- **Access**: Public / Authenticated
- **Response (200 OK)**: Returns medicine catalog records.

### Add / Update Medicine Stock
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

## 7. Administrator Endpoints (`/api/admin`)

### Register New Member
- **Endpoint**: `POST /add_member`
- **Access**: Admin only
- **Process**: Inserts account into the authentication table and routes entity data to the target shard.

### Delete Member
- **Endpoint**: `DELETE /member/<id>`
- **Access**: Admin only
- **Process**: Deletes member record from authentication and corresponding shard table.
