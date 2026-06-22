"""
Campaign and outbound email background tasks
"""

from app.tasks.async_runner import run_async
from app.tasks.celery_app import celery_app as celery
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_
from app.models.database import AsyncSessionLocal, UserEmailAccount
from app.models.campaign_models import Campaign, Lead, CampaignSequence, WarmupSchedule
from app.services.smtp_service import SMTPService
from app.core.security import logger



@celery.task(bind=True, max_retries=3)
def send_campaign_emails(self):
    """Sync wrapper for sending pending campaign emails"""
    return run_async(_send_campaign_emails(self))


async def _send_campaign_emails(self):
    """Async implementation executed via asyncio.run by the sync wrapper"""
    try:
        async with AsyncSessionLocal() as session:
            smtp_service = SMTPService()
            # Get active/running campaigns eligible to send
            result = await session.execute(
                select(Campaign).where(
                    and_(
                        Campaign.status == "running",
                        or_(Campaign.start_date == None, Campaign.start_date <= datetime.utcnow())
                    )
                ).limit(10)
            )
            campaigns = result.scalars().all()
            
            sent_count = 0
            
            for campaign in campaigns:
                try:
                    # Load first sequence step for content templates
                    seq_result = await session.execute(
                        select(CampaignSequence)
                        .where(CampaignSequence.campaign_id == campaign.id)
                        .order_by(CampaignSequence.step_order.asc())
                        .limit(1)
                    )
                    sequence = seq_result.scalar_one_or_none()

                    if not sequence:
                        logger.warning(f"Campaign {campaign.id} has no sequence steps; skipping")
                        continue

                    # Determine sender account
                    account = await _get_sender_account(session, campaign)
                    if not account:
                        logger.warning(f"No active email account found for campaign {campaign.id}; skipping")
                        continue

                    # Get leads with pending status
                    lead_result = await session.execute(
                        select(Lead).where(
                            and_(
                                Lead.campaign_id == campaign.id,
                                Lead.status == "pending"
                            )
                        ).limit(campaign.daily_send_limit or 50)
                    )
                    leads = lead_result.scalars().all()
                    
                    for lead in leads:
                        try:
                            # Personalize and send email
                            personalized_subject = sequence.subject_template.format(
                                first_name=lead.first_name or "",
                                company=lead.company or "",
                                email=lead.email
                            )
                            
                            personalized_body = sequence.body_template.format(
                                first_name=lead.first_name or "",
                                company=lead.company or "",
                                email=lead.email,
                                title=lead.job_title or ""
                            )
                            
                            # Send via SMTP service
                            sent, _message = await smtp_service.send_email(
                                account=account,
                                db=session,
                                to=lead.email,
                                subject=personalized_subject,
                                body_text=personalized_body,
                            )
                            
                            if sent:
                                lead.status = "sent"
                                lead.last_email_sent_at = datetime.utcnow()
                                campaign.emails_sent = (campaign.emails_sent or 0) + 1
                                sent_count += 1
                        
                        except Exception as e:
                            logger.error(f"Failed to send to lead {lead.id}: {str(e)}")
                            continue
                    
                    await session.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing campaign {campaign.id}: {str(e)}")
                    continue
            
            logger.info(f"Sent {sent_count} campaign emails")
            return {"sent": sent_count, "status": "success"}
    
    except Exception as exc:
        logger.error(f"send_campaign_emails failed: {str(exc)}")
        self.retry(exc=exc, countdown=60)


@celery.task(bind=True, max_retries=2)
def process_campaign_replies(self):
    """Sync wrapper for processing campaign replies"""
    return run_async(_process_campaign_replies(self))


async def _process_campaign_replies(self):
    """Async implementation executed via asyncio.run by the sync wrapper"""
    try:
        async with AsyncSessionLocal() as session:
            # Get leads with replies
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.replied_at.isnot(None),
                        Lead.status == "sent"
                    )
                ).limit(100)
            )
            leads = result.scalars().all()
            
            processed = 0
            for lead in leads:
                try:
                    # Mark as replied
                    lead.status = "replied"
                    lead.last_replied_at = datetime.utcnow()
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing reply for lead {lead.id}: {str(e)}")
                    continue
            
            await session.commit()
            logger.info(f"Processed {processed} campaign replies")
            return {"processed": processed, "status": "success"}
    
    except Exception as exc:
        logger.error(f"process_campaign_replies failed: {str(exc)}")
        self.retry(exc=exc, countdown=30)


@celery.task(bind=True, max_retries=1)
def execute_warmup_schedule(self):
    """Sync wrapper for executing warmup schedule"""
    return run_async(_execute_warmup_schedule(self))


async def _execute_warmup_schedule(self):
    """Async implementation executed via asyncio.run by the sync wrapper"""
    try:
        async with AsyncSessionLocal() as session:
            # Get today's warmup schedules
            today = datetime.utcnow().strftime("%A")
            
            result = await session.execute(
                select(WarmupSchedule).where(
                    and_(
                        WarmupSchedule.day_of_week == today,
                        WarmupSchedule.is_active == True
                    )
                )
            )
            schedules = result.scalars().all()
            
            executed = 0
            for schedule in schedules:
                try:
                    # Load first sequence step for content templates
                    seq_result = await session.execute(
                        select(CampaignSequence)
                        .where(CampaignSequence.campaign_id == schedule.campaign_id)
                        .order_by(CampaignSequence.step_order.asc())
                        .limit(1)
                    )
                    sequence = seq_result.scalar_one_or_none()
                    if not sequence:
                        logger.warning(f"Campaign {schedule.campaign_id} has no sequence steps; skipping warmup")
                        continue

                    # Get pending leads for this campaign
                    lead_result = await session.execute(
                        select(Lead).where(
                            and_(
                                Lead.campaign_id == schedule.campaign_id,
                                Lead.status == "pending"
                            )
                        ).limit(schedule.send_limit)
                    )
                    leads = lead_result.scalars().all()
                    
                    for lead in leads:
                        # Send warmup email
                        campaign = await session.get(Campaign, schedule.campaign_id)
                        if campaign:
                            account = await _get_sender_account(session, campaign)
                            if not account:
                                logger.warning(f"No active email account for campaign {campaign.id}; skipping lead {lead.id}")
                                continue

                            smtp_service = SMTPService()
                            sent, _message = await smtp_service.send_email(
                                account=account,
                                db=session,
                                to=lead.email,
                                subject=sequence.subject_template,
                                body_text=sequence.body_template,
                            )
                            
                            if sent:
                                lead.status = "sent"
                                lead.last_email_sent_at = datetime.utcnow()
                                executed += 1
                    
                    schedule.last_executed = datetime.utcnow()
                    schedule.emails_sent_today = len(leads)
                    
                except Exception as e:
                    logger.error(f"Error executing warmup schedule {schedule.id}: {str(e)}")
                    continue
            
            await session.commit()
            logger.info(f"Executed warmup schedule for {executed} emails")
            return {"executed": executed, "status": "success"}
    
    except Exception as exc:
        logger.error(f"execute_warmup_schedule failed: {str(exc)}")
        self.retry(exc=exc, countdown=30)


async def _get_sender_account(session, campaign: Campaign) -> UserEmailAccount:
    """Get the active sender account for a campaign."""
    # Prefer exact match on from_email if present
    if campaign.from_email:
        result = await session.execute(
            select(UserEmailAccount).where(
                and_(
                    UserEmailAccount.user_id == campaign.user_id,
                    UserEmailAccount.email == campaign.from_email,
                    UserEmailAccount.is_active == True
                )
            ).limit(1)
        )
        account = result.scalar_one_or_none()
        if account:
            return account

    # Fallback to primary active account
    result = await session.execute(
        select(UserEmailAccount).where(
            and_(
                UserEmailAccount.user_id == campaign.user_id,
                UserEmailAccount.is_active == True
            )
        ).order_by(UserEmailAccount.is_primary.desc(), UserEmailAccount.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()
