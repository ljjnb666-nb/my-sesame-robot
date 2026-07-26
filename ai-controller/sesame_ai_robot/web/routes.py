from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .schemas import ChatRequest, EmptyRequest, FaultRequest
from .service import RobotSimulatorService


def create_router(get_service) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health(service: RobotSimulatorService = Depends(get_service)):
        return service.health()

    @router.post("/chat")
    def chat(request: ChatRequest, service: RobotSimulatorService = Depends(get_service)):
        return service.chat(request.text, request.confirmationId)

    @router.get("/state")
    def state(service: RobotSimulatorService = Depends(get_service)):
        return service.state()

    @router.get("/timeline")
    def timeline(
        limit: int = Query(default=20),
        service: RobotSimulatorService = Depends(get_service),
    ):
        return service.timeline(limit)

    @router.post("/simulator/faults")
    def inject_fault(request: FaultRequest, service: RobotSimulatorService = Depends(get_service)):
        return service.inject_fault(request.fault)

    @router.delete("/simulator/faults/{fault}")
    def clear_fault(fault: str, service: RobotSimulatorService = Depends(get_service)):
        return service.clear_fault(fault)

    @router.post("/simulator/reset")
    def reset_simulator(request: EmptyRequest, service: RobotSimulatorService = Depends(get_service)):
        return service.reset_simulator()

    @router.post("/session/reset")
    def reset_session(request: EmptyRequest, service: RobotSimulatorService = Depends(get_service)):
        return service.reset_session()

    return router
