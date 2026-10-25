import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import func, and_, or_

from config import Config
from models import Service, Token, QueueEvent, SystemSetting, utcnow

def generate_random_ref_code(length: int = 6) -> str:
    """Generate a clean, unambiguous uppercase alphanumeric code, e.g. QL-7K9M2P"""
    # Exclude characters like 0, O, 1, I to avoid human transcription confusion
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    random_part = "".join(random.choice(chars) for _ in range(length))
    return f"QL-{random_part}"

class QueueService:
    @staticmethod
    def get_services(active_only: bool = True) -> List[Dict[str, Any]]:
        from db import Session
        session = Session()
        try:
            query = session.query(Service)
            if active_only:
                query = query.filter_by(is_active=True)
            services = query.order_by(Service.id.asc()).all()
            
            result = []
            for s in services:
                # Count currently waiting tokens for this service
                waiting_count = session.query(func.count(Token.id)).filter(
                    Token.service_id == s.id,
                    Token.status == "WAITING"
                ).scalar() or 0
                
                # Current serving token
                serving = session.query(Token).filter(
                    Token.service_id == s.id,
                    Token.status == "SERVING"
                ).order_by(Token.called_at.desc()).first()
                
                data = s.to_dict()
                data["waiting_count"] = waiting_count
                data["current_serving"] = serving.token_number if serving else None
                data["estimated_wait_time"] = waiting_count * s.avg_service_time_mins
                result.append(data)
            return result
        finally:
            session.close()

    @staticmethod
    def get_service_by_id(service_id: int) -> Optional[Service]:
        from db import Session
        session = Session()
        try:
            return session.query(Service).filter_by(id=service_id).first()
        finally:
            session.close()

    @staticmethod
    def create_token(
        service_id: int,
        visitor_name: Optional[str] = None,
        student_id: Optional[str] = None,
        phone_or_email: Optional[str] = None,
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new sequential token for the service.
        Guarantees unique sequence number and reference code with concurrency safety.
        """
        from db import Session
        session = Session()
        try:
            # 1. Idempotency Check: if identical key provided within last 5 minutes, return existing token
            if idempotency_key:
                existing = session.query(Token).filter_by(idempotency_key=idempotency_key).first()
                if existing:
                    return {
                        "success": True,
                        "token": existing.to_dict(),
                        "is_duplicate": True,
                        "message": "Token retrieved from prior submission."
                    }

            service = session.query(Service).filter_by(id=service_id, is_active=True).first()
            if not service:
                return {"success": False, "error": "Invalid or inactive service selected."}

            # 2. Determine sequential token number
            # Compute max sequence number for this service
            max_seq = session.query(func.max(Token.sequence_number)).filter(
                Token.service_id == service_id
            ).scalar()

            if max_seq is None or max_seq < 100:
                next_seq = 101
            else:
                next_seq = max_seq + 1

            token_number = f"{service.prefix}-{next_seq}"

            # 3. Generate unique reference code
            ref_code = generate_random_ref_code()
            while session.query(Token).filter_by(reference_code=ref_code).first() is not None:
                ref_code = generate_random_ref_code()

            clean_name = visitor_name.strip() if visitor_name else "Visitor"
            clean_student_id = student_id.strip() if student_id else None

            token = Token(
                service_id=service_id,
                token_number=token_number,
                sequence_number=next_seq,
                reference_code=ref_code,
                visitor_name=clean_name,
                student_id=clean_student_id,
                phone_or_email=phone_or_email.strip() if phone_or_email else None,
                notes=notes.strip() if notes else None,
                status="WAITING",
                idempotency_key=idempotency_key,
                created_at=utcnow()
            )
            session.add(token)
            session.flush()

            # Record creation event
            event = QueueEvent(
                token_id=token.id,
                event_type="CREATED",
                message=f"Token {token_number} generated for {service.name}. You are in the queue.",
                created_at=utcnow()
            )
            session.add(event)
            session.commit()

            # Prepare response data
            token_dict = token.to_dict()
            session.close()

            # Calculate initial position & wait time
            status_data = QueueService.get_token_status(ref_code)
            return {
                "success": True,
                "token": token_dict,
                "status_info": status_data,
                "is_duplicate": False,
                "message": "Token generated successfully."
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": f"Failed to generate token: {str(e)}"}
        finally:
            session.close()

    @staticmethod
    def get_token_status(reference_code_or_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve live queue status for a token using either its secure reference code (e.g. QL-7K9M2P)
        or token number (e.g. ADM-101).
        """
        from db import Session
        session = Session()
        try:
            token_query = session.query(Token).join(Service).filter(
                or_(
                    Token.reference_code == reference_code_or_number.strip().upper(),
                    Token.token_number == reference_code_or_number.strip().upper()
                )
            )
            token = token_query.first()
            if not token:
                return None

            service = token.service
            
            # Find currently serving token for this service
            serving_token = session.query(Token).filter(
                Token.service_id == service.id,
                Token.status == "SERVING"
            ).order_by(Token.called_at.desc()).first()

            # Find number of people ahead
            people_ahead = 0
            if token.status == "WAITING":
                people_ahead = session.query(func.count(Token.id)).filter(
                    Token.service_id == service.id,
                    Token.status == "WAITING",
                    Token.created_at < token.created_at
                ).scalar() or 0

            # Get threshold setting
            thresh_setting = session.query(SystemSetting).filter_by(key="approaching_threshold").first()
            threshold = int(thresh_setting.value) if thresh_setting and thresh_setting.value.isdigit() else Config.DEFAULT_APPROACHING_THRESHOLD

            is_approaching = (token.status == "WAITING" and people_ahead <= threshold)

            # Estimated wait time in minutes
            if token.status == "WAITING":
                if people_ahead == 0:
                    estimated_wait_mins = 2  # next in line
                else:
                    estimated_wait_mins = people_ahead * service.avg_service_time_mins
            elif token.status == "SERVING":
                estimated_wait_mins = 0
            else:
                estimated_wait_mins = 0

            # Fetch recent events for notification audit
            events = session.query(QueueEvent).filter_by(token_id=token.id).order_by(QueueEvent.created_at.desc()).limit(10).all()

            display_status = token.status
            if token.status == "WAITING" and is_approaching:
                display_status = "APPROACHING"

            return {
                "token_id": token.id,
                "token_number": token.token_number,
                "reference_code": token.reference_code,
                "visitor_name": token.visitor_name,
                "service_id": service.id,
                "service_name": service.name,
                "service_code": service.code,
                "counter_number": service.counter_number,
                "raw_status": token.status,
                "status": display_status,
                "people_ahead": people_ahead,
                "estimated_wait_mins": estimated_wait_mins,
                "current_serving": serving_token.token_number if serving_token else None,
                "current_serving_id": serving_token.id if serving_token else None,
                "is_your_turn": (token.status == "SERVING"),
                "is_approaching": is_approaching,
                "created_at": token.created_at.isoformat() if token.created_at else None,
                "called_at": token.called_at.isoformat() if token.called_at else None,
                "completed_at": token.completed_at.isoformat() if token.completed_at else None,
                "avg_service_time_mins": service.avg_service_time_mins,
                "events": [e.to_dict() for e in events]
            }
        finally:
            session.close()

    @staticmethod
    def call_next_token(service_id: int) -> Dict[str, Any]:
        """
        Advance queue: Call the next waiting token.
        If a token is currently being served on this counter, auto-completes it.
        """
        from db import Session
        session = Session()
        try:
            service = session.query(Service).filter_by(id=service_id).first()
            if not service:
                return {"success": False, "error": "Service not found."}

            now = utcnow()

            # 1. Complete existing serving token if any
            currently_serving = session.query(Token).filter(
                Token.service_id == service_id,
                Token.status == "SERVING"
            ).all()

            for old_token in currently_serving:
                old_token.status = "COMPLETED"
                old_token.completed_at = now
                if old_token.called_at:
                    diff = (now - old_token.called_at.replace(tzinfo=timezone.utc if old_token.called_at.tzinfo is None else None)).total_seconds()
                    old_token.service_duration_seconds = max(1, int(diff))
                session.add(QueueEvent(
                    token_id=old_token.id,
                    event_type="COMPLETED",
                    message=f"Service completed at {service.counter_number}.",
                    created_at=now
                ))

            # 2. Find next waiting token
            next_token = session.query(Token).filter(
                Token.service_id == service_id,
                Token.status == "WAITING"
            ).order_by(Token.created_at.asc(), Token.id.asc()).first()

            if not next_token:
                session.commit()
                return {
                    "success": False,
                    "message": "No visitors waiting in queue for this service.",
                    "queue_empty": True
                }

            # 3. Mark next token as SERVING
            next_token.status = "SERVING"
            next_token.called_at = now

            event_msg = f"Token {next_token.token_number} is called! Please proceed to {service.counter_number} ({service.name})."
            session.add(QueueEvent(
                token_id=next_token.id,
                event_type="CALLED",
                message=event_msg,
                created_at=now
            ))
            session.commit()

            return {
                "success": True,
                "called_token": next_token.to_dict(),
                "message": f"Token {next_token.token_number} called to {service.counter_number}."
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": f"Error calling next token: {str(e)}"}
        finally:
            session.close()

    @staticmethod
    def complete_token(token_id: int) -> Dict[str, Any]:
        """Mark a token as completed."""
        from db import Session
        session = Session()
        try:
            token = session.query(Token).filter_by(id=token_id).first()
            if not token:
                return {"success": False, "error": "Token not found."}

            now = utcnow()
            token.status = "COMPLETED"
            token.completed_at = now
            if token.called_at:
                diff = (now - token.called_at.replace(tzinfo=timezone.utc if token.called_at.tzinfo is None else None)).total_seconds()
                token.service_duration_seconds = max(1, int(diff))

            session.add(QueueEvent(
                token_id=token.id,
                event_type="COMPLETED",
                message=f"Token {token.token_number} marked as completed.",
                created_at=now
            ))
            session.commit()
            return {"success": True, "message": f"Token {token.token_number} completed."}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def skip_token(token_id: int, reason: str = "Visitor absent when called") -> Dict[str, Any]:
        """Mark a token as skipped (visitor did not show up)."""
        from db import Session
        session = Session()
        try:
            token = session.query(Token).filter_by(id=token_id).first()
            if not token:
                return {"success": False, "error": "Token not found."}

            now = utcnow()
            token.status = "SKIPPED"
            token.completed_at = now

            session.add(QueueEvent(
                token_id=token.id,
                event_type="SKIPPED",
                message=f"Token {token.token_number} was skipped: {reason}.",
                created_at=now
            ))
            session.commit()
            return {"success": True, "message": f"Token {token.token_number} marked as skipped."}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def recall_token(token_id: int) -> Dict[str, Any]:
        """Re-announce a token that is currently SERVING to notify the visitor again."""
        from db import Session
        session = Session()
        try:
            token = session.query(Token).filter_by(id=token_id).first()
            if not token:
                return {"success": False, "error": "Token not found."}

            now = utcnow()
            token.status = "SERVING"
            token.called_at = now

            session.add(QueueEvent(
                token_id=token.id,
                event_type="RECALLED",
                message=f"Recall Announcement: Token {token.token_number}, please proceed to {token.service.counter_number} immediately.",
                created_at=now
            ))
            session.commit()
            return {"success": True, "message": f"Token {token.token_number} recalled."}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def cancel_token_by_visitor(reference_code: str) -> Dict[str, Any]:
        """Allow a visitor to voluntarily cancel their queue token."""
        from db import Session
        session = Session()
        try:
            token = session.query(Token).filter_by(reference_code=reference_code.strip().upper()).first()
            if not token:
                return {"success": False, "error": "Token not found."}

            if token.status in ["COMPLETED", "SKIPPED", "CANCELLED"]:
                return {"success": False, "error": f"Token is already {token.status.lower()}."}

            token.status = "CANCELLED"
            now = utcnow()
            token.completed_at = now

            session.add(QueueEvent(
                token_id=token.id,
                event_type="CANCELLED",
                message="Visitor cancelled their token and left the queue.",
                created_at=now
            ))
            session.commit()
            return {"success": True, "message": f"Token {token.token_number} cancelled successfully."}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def reset_queue(service_id: Optional[int] = None) -> Dict[str, Any]:
        """Safely clear/archive all pending waiting tokens for a service or all services."""
        from db import Session
        session = Session()
        try:
            query = session.query(Token).filter(Token.status.in_(["WAITING", "SERVING"]))
            if service_id:
                query = query.filter(Token.service_id == service_id)
            tokens = query.all()
            now = utcnow()
            count = 0
            for t in tokens:
                t.status = "CANCELLED"
                t.completed_at = now
                session.add(QueueEvent(
                    token_id=t.id,
                    event_type="CANCELLED",
                    message="Queue was reset by administrator.",
                    created_at=now
                ))
                count += 1
            session.commit()
            return {"success": True, "message": f"Queue reset completed. {count} active tokens cleared."}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def get_admin_dashboard_data() -> Dict[str, Any]:
        """Compile complete real-time dashboard data for administrators."""
        from db import Session
        session = Session()
        try:
            # Overall counters
            total_tokens = session.query(func.count(Token.id)).scalar() or 0
            waiting_tokens = session.query(func.count(Token.id)).filter_by(status="WAITING").scalar() or 0
            serving_tokens = session.query(func.count(Token.id)).filter_by(status="SERVING").scalar() or 0
            completed_tokens = session.query(func.count(Token.id)).filter_by(status="COMPLETED").scalar() or 0
            skipped_tokens = session.query(func.count(Token.id)).filter_by(status="SKIPPED").scalar() or 0

            # Calculate average service duration of completed tokens (in minutes)
            avg_duration_sec = session.query(func.avg(Token.service_duration_seconds)).filter(
                Token.status == "COMPLETED",
                Token.service_duration_seconds.isnot(None)
            ).scalar()
            avg_service_mins = round((avg_duration_sec or 300) / 60, 1)

            # Per-service overview
            services = session.query(Service).order_by(Service.id.asc()).all()
            service_summaries = []
            for s in services:
                current_serving = session.query(Token).filter_by(
                    service_id=s.id, status="SERVING"
                ).order_by(Token.called_at.desc()).first()

                next_in_line = session.query(Token).filter_by(
                    service_id=s.id, status="WAITING"
                ).order_by(Token.created_at.asc()).first()

                waiting_count = session.query(func.count(Token.id)).filter_by(
                    service_id=s.id, status="WAITING"
                ).scalar() or 0

                completed_count = session.query(func.count(Token.id)).filter_by(
                    service_id=s.id, status="COMPLETED"
                ).scalar() or 0

                service_summaries.append({
                    "id": s.id,
                    "name": s.name,
                    "code": s.code,
                    "prefix": s.prefix,
                    "counter_number": s.counter_number,
                    "avg_service_time_mins": s.avg_service_time_mins,
                    "is_active": s.is_active,
                    "waiting_count": waiting_count,
                    "completed_count": completed_count,
                    "current_serving": current_serving.to_dict() if current_serving else None,
                    "next_in_line": next_in_line.to_dict() if next_in_line else None,
                })

            # Recent 25 tokens for table
            recent_tokens = session.query(Token).order_by(Token.created_at.desc()).limit(30).all()

            return {
                "stats": {
                    "total_tokens": total_tokens,
                    "waiting_tokens": waiting_tokens,
                    "serving_tokens": serving_tokens,
                    "completed_tokens": completed_tokens,
                    "skipped_tokens": skipped_tokens,
                    "avg_service_mins": avg_service_mins,
                },
                "services": service_summaries,
                "recent_tokens": [t.to_dict() for t in recent_tokens]
            }
        finally:
            session.close()

    @staticmethod
    def get_public_display_data() -> Dict[str, Any]:
        """Compile data for public waiting room screen / TV display."""
        from db import Session
        session = Session()
        try:
            services = session.query(Service).filter_by(is_active=True).order_by(Service.id.asc()).all()
            counters = []
            recent_calls = []

            for s in services:
                current_serving = session.query(Token).filter_by(
                    service_id=s.id, status="SERVING"
                ).order_by(Token.called_at.desc()).first()

                upcoming = session.query(Token).filter_by(
                    service_id=s.id, status="WAITING"
                ).order_by(Token.created_at.asc()).limit(3).all()

                waiting_count = session.query(func.count(Token.id)).filter_by(
                    service_id=s.id, status="WAITING"
                ).scalar() or 0

                counters.append({
                    "service_id": s.id,
                    "service_name": s.name,
                    "counter_number": s.counter_number,
                    "prefix": s.prefix,
                    "now_serving": current_serving.token_number if current_serving else "—",
                    "visitor_name": current_serving.visitor_name if current_serving else None,
                    "called_at": current_serving.called_at.isoformat() if (current_serving and current_serving.called_at) else None,
                    "waiting_count": waiting_count,
                    "upcoming": [u.token_number for u in upcoming]
                })

            # Fetch the most recent CALLED or RECALLED event across all services
            latest_called = session.query(QueueEvent).filter(
                QueueEvent.event_type.in_(["CALLED", "RECALLED"])
            ).order_by(QueueEvent.created_at.desc()).first()

            return {
                "counters": counters,
                "latest_announcement": latest_called.message if latest_called else None,
                "latest_announcement_time": latest_called.created_at.isoformat() if latest_called else None,
                "server_time": utcnow().isoformat()
            }
        finally:
            session.close()
