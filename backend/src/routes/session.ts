import { Router } from "express";

import {
    createSession,
    getSession,
    addEvent,
    finishSession,
    getReport
} from "../controllers/session.js";

import {
    validateCreateSession,
    validateSessionId,
    validateEvent
} from "../middleware/validation.js";

const router = Router();

router.post(
    "/session",
    validateCreateSession,
    createSession
);

router.get(
    "/session/:id",
    validateSessionId,
    getSession
);

router.post(
    "/session/:id/event",
    validateSessionId,
    validateEvent,
    addEvent
);

router.post(
    "/session/:id/finish",
    validateSessionId,
    finishSession
);

router.get(
    "/session/:id/report",
    validateSessionId,
    getReport
);

export default router;