import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid
from dataclasses import dataclass, asdict
import pickle
from pathlib import Path

from shared.models import JobInfo, JobStatus, JobType

logger = logging.getLogger(__name__)

@dataclass
class JobTask:
    """Individual task within a job"""
    task_id: str
    task_type: str
    task_name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Any] = None
    progress: float = 0.0

class JobQueue:
    """In-memory job queue for async task processing"""
    
    def __init__(self):
        self.jobs: Dict[str, JobInfo] = {}
        self.job_tasks: Dict[str, List[JobTask]] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.max_concurrent_jobs = 3
        self.job_timeout_minutes = 60
        self.cleanup_interval_minutes = 30
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the job queue"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting job queue")
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Register default task handlers
        await self._register_default_handlers()
    
    async def stop(self):
        """Stop the job queue"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Job queue stopped")
    
    async def create_job(
        self,
        job_type: JobType,
        job_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Create a new job"""
        try:
            job_id = str(uuid.uuid4())
            
            # Create job info
            job_info = JobInfo(
                job_id=job_id,
                job_type=job_type,
                status=JobStatus.PENDING,
                created_at=datetime.now(),
                created_by=user_id,
                job_data=job_data
            )
            
            # Store job
            self.jobs[job_id] = job_info
            
            # Create job tasks based on job type
            tasks = self._create_job_tasks(job_type, job_data)
            self.job_tasks[job_id] = tasks
            
            logger.info(f"Created job {job_id} of type {job_type.value} with {len(tasks)} tasks")
            
            # Start job processing
            asyncio.create_task(self._process_job(job_id))
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Get job status"""
        return self.jobs.get(job_id)
    
    async def get_job_tasks(self, job_id: str) -> List[JobTask]:
        """Get job tasks"""
        return self.job_tasks.get(job_id, [])
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                return False
            
            # Update job status
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            
            # Cancel all tasks
            tasks = self.job_tasks.get(job_id, [])
            for task in tasks:
                if task.status == JobStatus.RUNNING:
                    task.status = JobStatus.CANCELLED
                    task.completed_at = datetime.now()
            
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    async def register_task_handler(self, task_type: str, handler: Callable):
        """Register a task handler"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered task handler for {task_type}")
    
    async def _create_job_tasks(self, job_type: JobType, job_data: Dict[str, Any]) -> List[JobTask]:
        """Create tasks for a job based on its type"""
        tasks = []
        
        if job_type == JobType.DOCUMENT_PROCESSING:
            # Document processing pipeline
            task_configs = [
                ("ocr_extraction", "OCR Text Extraction"),
                ("field_extraction", "Field Data Extraction"),
                ("cross_validation", "Cross-Validation Checks"),
                ("credit_scoring", "Five Cs Credit Scoring"),
                ("loan_limit_calc", "Loan Limit Calculation"),
                ("cam_generation", "CAM Document Generation")
            ]
        elif job_type == JobType.RESEARCH_ANALYSIS:
            # Research analysis pipeline
            task_configs = [
                ("research_planning", "Research Planning"),
                ("external_data_fetch", "External Data Fetch"),
                ("risk_synthesis", "Risk Synthesis"),
                ("report_generation", "Research Report Generation")
            ]
        elif job_type == JobType.OFFICER_ANALYSIS:
            # Officer analysis pipeline
            task_configs = [
                ("nlp_classification", "NLP Classification"),
                ("score_adjustment", "Score Adjustment"),
                ("explanation_generation", "Explanation Generation")
            ]
        else:
            # Generic job
            task_configs = [
                ("generic_task", "Generic Task Processing")
            ]
        
        for task_type, task_name in task_configs:
            task = JobTask(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                task_name=task_name,
                status=JobStatus.PENDING
            )
            tasks.append(task)
        
        return tasks
    
    async def _process_job(self, job_id: str):
        """Process a job"""
        try:
            job = self.jobs.get(job_id)
            if not job:
                return
            
            # Check concurrent job limit
            running_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
            if running_jobs >= self.max_concurrent_jobs:
                # Wait for a running job to complete
                await self._wait_for_job_slot()
            
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            
            logger.info(f"Processing job {job_id}")
            
            # Process tasks sequentially
            tasks = self.job_tasks.get(job_id, [])
            for task in tasks:
                if job.status == JobStatus.CANCELLED:
                    break
                
                await self._process_task(job_id, task)
                
                # Update job progress
                completed_tasks = sum(1 for t in tasks if t.status == JobStatus.COMPLETED)
                job.progress = (completed_tasks / len(tasks)) * 100
                
                # Check if task failed
                if task.status == JobStatus.FAILED:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Task {task.task_name} failed: {task.error_message}"
                    job.completed_at = datetime.now()
                    break
            
            # Update final job status
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 100.0
            
            logger.info(f"Completed job {job_id} with status {job.status.value}")
            
        except Exception as e:
            logger.error(f"Job processing failed for {job_id}: {e}")
            
            # Update job status
            job = self.jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now()
    
    async def _process_task(self, job_id: str, task: TaskTask):
        """Process a single task"""
        try:
            # Update task status
            task.status = JobStatus.RUNNING
            task.started_at = datetime.now()
            
            logger.info(f"Processing task {task.task_type} for job {job_id}")
            
            # Get task handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                task.status = JobStatus.FAILED
                task.error_message = f"No handler registered for task type {task.task_type}"
                task.completed_at = datetime.now()
                return
            
            # Execute task handler
            job_data = self.jobs[job_id].job_data
            result = await handler(job_data, task)
            
            # Update task with result
            task.result = result
            task.status = JobStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            
            logger.info(f"Completed task {task.task_type} for job {job_id}")
            
        except Exception as e:
            logger.error(f"Task processing failed for {task.task_type}: {e}")
            
            task.status = JobStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
    
    async def _wait_for_job_slot(self):
        """Wait for a job slot to become available"""
        while True:
            running_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
            if running_jobs < self.max_concurrent_jobs:
                break
            
            await asyncio.sleep(1)
    
    async def _register_default_handlers(self):
        """Register default task handlers"""
        # OCR extraction handler
        await self.register_task_handler("ocr_extraction", self._handle_ocr_extraction)
        
        # Field extraction handler
        await self.register_task_handler("field_extraction", self._handle_field_extraction)
        
        # Cross validation handler
        await self.register_task_handler("cross_validation", self._handle_cross_validation)
        
        # Credit scoring handler
        await self.register_task_handler("credit_scoring", self._handle_credit_scoring)
        
        # Loan limit calculation handler
        await self.register_task_handler("loan_limit_calc", self._handle_loan_limit_calc)
        
        # CAM generation handler
        await self.register_task_handler("cam_generation", self._handle_cam_generation)
        
        # Research planning handler
        await self.register_task_handler("research_planning", self._handle_research_planning)
        
        # External data fetch handler
        await self.register_task_handler("external_data_fetch", self._handle_external_data_fetch)
        
        # Risk synthesis handler
        await self.register_task_handler("risk_synthesis", self._handle_risk_synthesis)
        
        # NLP classification handler
        await self.register_task_handler("nlp_classification", self._handle_nlp_classification)
    
    async def _handle_ocr_extraction(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle OCR extraction task"""
        from pillar1_ingestor.ocr_pipeline import ocr_pipeline
        
        # Simulate OCR processing
        await asyncio.sleep(2)
        
        # Mock result
        return {
            "extracted_text": "Mock OCR extraction completed",
            "confidence": 0.95,
            "processing_time": 2.0
        }
    
    async def _handle_field_extraction(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle field extraction task"""
        # Simulate field extraction
        await asyncio.sleep(3)
        
        # Mock result
        return {
            "extracted_fields": {
                "revenue": 10000000,
                "ebitda": 2000000,
                "pat": 1500000
            },
            "extraction_confidence": 0.88
        }
    
    async def _handle_cross_validation(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle cross validation task"""
        # Simulate cross validation
        await asyncio.sleep(1)
        
        # Mock result
        return {
            "validation_flags": [],
            "validation_score": 0.92
        }
    
    async def _handle_credit_scoring(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle credit scoring task"""
        from pillar3_engine.five_cs_scorer import five_cs_scorer
        
        # Simulate credit scoring
        await asyncio.sleep(2)
        
        # Mock result
        return {
            "five_c_scores": {
                "character": 75,
                "capacity": 80,
                "capital": 70,
                "collateral": 65,
                "conditions": 72
            },
            "total_score": 73.0,
            "grade": "MODERATE_RISK"
        }
    
    async def _handle_loan_limit_calc(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle loan limit calculation task"""
        # Simulate loan limit calculation
        await asyncio.sleep(1)
        
        # Mock result
        return {
            "loan_limits": {
                "cash_flow_ceiling": 5000000,
                "asset_ceiling": 8000000,
                "sector_ceiling": 6000000,
                "final_limit": 5000000
            },
            "dscr": 1.8
        }
    
    async def _handle_cam_generation(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle CAM generation task"""
        # Simulate CAM generation
        await asyncio.sleep(4)
        
        # Mock result
        return {
            "cam_document": {
                "word_path": "/tmp/cam_output.docx",
                "pdf_path": "/tmp/cam_output.pdf",
                "generated_at": datetime.now().isoformat()
            }
        }
    
    async def _handle_research_planning(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle research planning task"""
        # Simulate research planning
        await asyncio.sleep(1)
        
        # Mock result
        return {
            "research_plan": {
                "ecourts": "Search for pending legal cases",
                "mca21": "Check director profiles",
                "news": "Search recent news",
                "rbi": "Check regulatory circulars"
            }
        }
    
    async def _handle_external_data_fetch(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle external data fetch task"""
        # Simulate external data fetch
        await asyncio.sleep(3)
        
        # Mock result
        return {
            "external_data": {
                "ecourts_cases": [],
                "mca21_directors": [],
                "news_articles": [],
                "rbi_circulars": []
            }
        }
    
    async def _handle_risk_synthesis(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle risk synthesis task"""
        # Simulate risk synthesis
        await asyncio.sleep(2)
        
        # Mock result
        return {
            "risk_findings": [],
            "risk_summary": "Low risk profile detected"
        }
    
    async def _handle_nlp_classification(self, job_data: Dict[str, Any], task: JobTask) -> Dict[str, Any]:
        """Handle NLP classification task"""
        # Simulate NLP classification
        await asyncio.sleep(1)
        
        # Mock result
        return {
            "classifications": [],
            "score_adjustments": {
                "character": 0,
                "capacity": 0,
                "capital": 0,
                "collateral": 0,
                "conditions": 0
            }
        }
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old jobs"""
        while self._running:
            try:
                await self._cleanup_old_jobs()
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_jobs(self):
        """Clean up old completed jobs"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            jobs_to_remove = []
            for job_id, job in self.jobs.items():
                if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                    job.completed_at and job.completed_at < cutoff_time):
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                if job_id in self.job_tasks:
                    del self.job_tasks[job_id]
            
            if jobs_to_remove:
                logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
                
        except Exception as e:
            logger.error(f"Job cleanup failed: {e}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        total_jobs = len(self.jobs)
        pending_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.PENDING)
        running_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
        completed_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED)
        failed_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED)
        
        return {
            "total_jobs": total_jobs,
            "pending_jobs": pending_jobs,
            "running_jobs": running_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "registered_handlers": list(self.task_handlers.keys())
        }

# Global instance
job_queue = JobQueue()
