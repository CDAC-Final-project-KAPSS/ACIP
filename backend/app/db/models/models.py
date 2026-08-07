import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base

class UserRole(str, enum.Enum):
    employee = "employee"
    reviewer = "reviewer"
    admin = "admin"
    auditor = "auditor"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"

class CaseStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    INGESTED = "INGESTED"
    OCR_RUNNING = "OCR_RUNNING"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    VALIDATION_REVIEW = "VALIDATION_REVIEW"
    COMPLIANCE_PENDING = "COMPLIANCE_PENDING"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    FINAL_REVIEW = "FINAL_REVIEW"
    GENERATING = "GENERATING"
    READY = "READY"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class TradeDirection(str, enum.Enum):
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    UNKNOWN = "UNKNOWN"

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.employee)
    active = Column(Boolean, default=True)
    approval_status = Column(String, default="PENDING")
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String, nullable=True)

class ProcessingCase(Base):
    __tablename__ = "processing_cases"
    processing_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    trade_direction = Column(Enum(TradeDirection), default=TradeDirection.UNKNOWN)
    status = Column(Enum(CaseStatus), default=CaseStatus.UPLOADING)
    final_shipment_id = Column(String, nullable=True, unique=True)
    results = Column(JSONB, nullable=True) # Added for Slip and Extracted Data
    version = Column(Integer, default=1)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_id = Column(UUID(as_uuid=True), ForeignKey("processing_cases.processing_id"))
    file_name = Column(String, nullable=False)
    document_type = Column(String)
    mime_type = Column(String)
    storage_uri = Column(String)
    sha256 = Column(String)
    version = Column(Integer, default=1)
    parse_status = Column(String)

class DocumentPage(Base):
    __tablename__ = "document_pages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"))
    page_no = Column(Integer)
    raw_text = Column(String)
    confidence = Column(Float)
    width = Column(Float)
    height = Column(Float)

class OcrEvidence(Base):
    __tablename__ = "ocr_evidence"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"))
    page_no = Column(Integer)
    field_key = Column(String)
    raw_value = Column(String)
    bbox_json = Column(JSONB)
    confidence = Column(Float)
    parser = Column(String)
    run_id = Column(String)

# More models would be added here based on Section 7 of the specification.

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_id = Column(UUID(as_uuid=True), ForeignKey("processing_cases.processing_id"))
    event_type = Column(String)
    details = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
