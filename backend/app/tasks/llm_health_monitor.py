"""
LLM Provider Health Monitoring Task
Runs periodically (every 30 minutes) to check provider health status
Updates the database with health status for real-time admin visibility
"""
import asyncio
from datetime import datetime
from app.core.security import logger
from app.models.database import AsyncSessionLocal
from app.services.llm_orchestration_service import llm_service
from app.services.llm_provider_config_service import LLMProviderConfigService


async def check_llm_provider_health():
    """
    Automatically check health of all configured LLM providers
    This runs on a schedule (via Celery Beat or FastAPI background task)
    """
    try:
        logger.info("🏥 [LLM Health Monitor] Starting periodic health check...")
        
        async with AsyncSessionLocal() as session:
            # Get health status for all providers
            health_result = await llm_service.provider_health(
                session=session,
                include_live_checks=True
            )
            
            has_error = False
            error_details = []
            
            # Update database with health status for each provider
            for provider_health in health_result.get("providers", []):
                provider = provider_health.get("provider", "")
                is_healthy = provider_health.get("status") == "healthy"
                reason = provider_health.get("reason")
                
                try:
                    await LLMProviderConfigService.update_health(
                        session,
                        provider=provider,
                        healthy=is_healthy,
                        error=reason
                    )
                    
                    status_emoji = "✅" if is_healthy else "❌"
                    logger.info(f"{status_emoji} [LLM Health Monitor] {provider}: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
                    
                    if not is_healthy and reason:
                        has_error = True
                        error_details.append({
                            "provider": provider,
                            "issue": reason[:200]  # First 200 chars of error
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to update health for {provider}: {e}")
            
            # Log summary
            total_providers = len(health_result.get("providers", []))
            healthy_count = sum(1 for p in health_result.get("providers", []) if p.get("status") == "healthy")
            
            logger.info(f"🏥 [LLM Health Monitor] Summary: {healthy_count}/{total_providers} providers healthy")
            
            if error_details:
                logger.warning(f"⚠️ [LLM Health Monitor] Issues detected: {error_details}")
            
    except Exception as e:
        logger.error(f"❌ [LLM Health Monitor] Health check failed: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")


async def schedule_health_checks():
    """
    Run health checks every 30 minutes
    Can be called by FastAPI lifespan or Celery Beat
    """
    while True:
        try:
            await check_llm_provider_health()
        except Exception as e:
            logger.error(f"Health check task error: {e}")
        
        # Wait 30 minutes before next check
        await asyncio.sleep(30 * 60)
