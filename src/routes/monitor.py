from fastapi import APIRouter, Depends
from typing import Optional, Literal
from src.services.admin_auth import AdminAPIKeyAuth
from src.monitor import get_monitor


api_key_auth = AdminAPIKeyAuth()


router = APIRouter(
    dependencies=[Depends(api_key_auth.verify_api_key)],
    responses={
        401: {"description": "API Key não fornecida"},
        403: {"description": "API Key inválida"}
    }
)


@router.get(
    "/health",
    summary="Health Check",
    description="Verifica se o sistema de monitoramento está funcionando"
)
async def health_check():
    """Health check básico sem métricas pesadas"""
    monitor = get_monitor()
    return {
        "status": "healthy",
        "uptime_seconds": monitor.get_process_info().get("uptime_seconds", 0),
        "monitoring": "active"
    }


@router.get(
    "/",
    summary="Todas as Métricas",
    description="Retorna todas as métricas do sistema em um único endpoint"
)
async def get_all_metrics():
    """Retorna snapshot completo de todas as métricas"""
    monitor = get_monitor()
    return monitor.get_all_metrics()


@router.get(
    "/summary",
    summary="Resumo Executivo",
    description="Retorna um resumo conciso das principais métricas"
)
async def get_summary():
    """Resumo executivo para dashboards"""
    monitor = get_monitor()
    
    memory_info = monitor.get_memory_info()
    cpu_info = monitor.get_cpu_info()
    process_info = monitor.get_process_info()
    
    return {
        "status": "operational",
        "uptime": process_info.get("uptime_formatted", "N/A"),
        "memory_usage_mb": memory_info.get("process", {}).get("rss_mb", 0),
        "memory_percent": memory_info.get("process", {}).get("percent", 0),
        "cpu_percent": cpu_info.get("process", {}).get("percent", 0),
        "total_requests": process_info.get("requests", {}).get("total", 0),
        "error_rate": process_info.get("requests", {}).get("error_rate_percent", 0),
        "threads": process_info.get("threads", 0)
    }


@router.get(
    "/memory",
    summary="Métricas de Memória",
    description="Informações detalhadas sobre uso de memória"
)
async def get_memory_metrics():
    """Métricas completas de memória"""
    monitor = get_monitor()
    return monitor.get_memory_info()


@router.get(
    "/cpu",
    summary="Métricas de CPU",
    description="Informações detalhadas sobre uso de CPU"
)
async def get_cpu_metrics():
    """Métricas completas de CPU"""
    monitor = get_monitor()
    return monitor.get_cpu_info()


@router.get(
    "/disk",
    summary="Métricas de Disco",
    description="Informações sobre uso de disco e I/O"
)
async def get_disk_metrics():
    monitor = get_monitor()
    return monitor.get_disk_info()


@router.get(
    "/network",
    summary="Métricas de Rede",
    description="Informações sobre tráfego de rede"
)
async def get_network_metrics():
    monitor = get_monitor()
    return monitor.get_network_info()


@router.get(
    "/process",
    summary="Informações do Processo",
    description="Informações sobre o processo da aplicação"
)
async def get_process_metrics():
    monitor = get_monitor()
    return monitor.get_process_info()


@router.get(
    "/history",
    summary="Histórico de Métricas",
    description="Retorna histórico de métricas para análise temporal"
)
async def get_history(
    metric: Literal["all", "memory", "cpu", "response_time"] = "all",
    seconds: Optional[int] = None
):
    """
    Histórico de métricas
    
    - **metric**: Tipo de métrica (all, memory, cpu, response_time)
    - **seconds**: Últimos N segundos (opcional, padrão: todo histórico)
    """
    monitor = get_monitor()
    return monitor.get_history(metric=metric, seconds=seconds)


@router.get(
    "/history/memory",
    summary="Histórico de Memória",
    description="Histórico específico de uso de memória"
)
async def get_memory_history(
    seconds: Optional[int] = None
):
    """Histórico de memória com estatísticas"""
    monitor = get_monitor()
    history = monitor.get_history(metric="memory", seconds=seconds)
    
    return {
        **history,
        "stats": monitor.memory_history.get_stats()
    }


@router.get(
    "/history/cpu",
    summary="Histórico de CPU",
    description="Histórico específico de uso de CPU"
)
async def get_cpu_history(
    seconds: Optional[int] = None    
):
    """Histórico de CPU com estatísticas"""
    monitor = get_monitor()
    history = monitor.get_history(metric="cpu", seconds=seconds)
    
    return {
        **history,
        "stats": monitor.cpu_history.get_stats()
    }


@router.get(
    "/history/response-time",
    summary="Histórico de Tempo de Resposta",
    description="Histórico de tempos de resposta das requisições"
)
async def get_response_time_history(
    seconds: Optional[int] = None    
):
    """Histórico de tempos de resposta com estatísticas"""
    monitor = get_monitor()
    history = monitor.get_history(metric="response_time", seconds=seconds)
    
    return {
        **history,
        "stats": monitor.response_times.get_stats()
    }


@router.get(
    "/stats/requests",
    summary="Estatísticas de Requisições",
    description="Estatísticas detalhadas sobre requisições processadas"
)
async def get_request_stats():
    """Estatísticas de requisições"""
    monitor = get_monitor()
    process_info = monitor.get_process_info()
    
    return {
        "requests": process_info.get("requests", {}),
        "response_time": monitor.response_times.get_stats(),
        "uptime_seconds": process_info.get("uptime_seconds", 0)
    }


@router.get(
    "/stats/peaks",
    summary="Valores de Pico",
    description="Valores máximos registrados de uso de recursos"
)
async def get_peak_values():
    """Valores de pico de uso"""
    monitor = get_monitor()
    
    memory_info = monitor.get_memory_info()
    cpu_info = monitor.get_cpu_info()
    
    return {
        "memory_peak_mb": memory_info.get("process", {}).get("peak_mb", 0),
        "cpu_peak_percent": cpu_info.get("process", {}).get("peak_percent", 0),
        "memory_stats": monitor.memory_history.get_stats(),
        "cpu_stats": monitor.cpu_history.get_stats()
    }


@router.post(
    "/reset",
    summary="Resetar Contadores",
    description="Reseta contadores de requests, erros e picos"
)
async def reset_counters():
    """Reset de contadores"""
    monitor = get_monitor()
    monitor.reset_counters()
    
    return {
        "status": "success",
        "message": "Contadores resetados com sucesso",
        "reset_items": ["request_count", "error_count", "peak_memory", "peak_cpu"]
    }


@router.post(
    "/history/clear",
    summary="Limpar Histórico",
    description="Limpa todo o histórico de métricas armazenado"
)
async def clear_history():
    """Limpa histórico de métricas"""
    monitor = get_monitor()
    monitor.clear_history()
    
    return {
        "status": "success",
        "message": "Histórico limpo com sucesso",
        "cleared_items": ["memory_history", "cpu_history", "response_times"]
    }


@router.post(
    "/update",
    summary="Atualizar Histórico",
    description="Força atualização imediata do histórico de métricas"
)
async def force_update():
    """Força atualização do histórico"""
    monitor = get_monitor()
    monitor.update_history()
    
    return {
        "status": "success",
        "message": "Histórico atualizado",
        "timestamp": monitor.get_all_metrics()["timestamp"]
    }