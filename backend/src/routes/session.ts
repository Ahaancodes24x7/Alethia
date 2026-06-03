import { Router } from "express";

import {
    createSession,
    getSession,
    addEvent,
    finishSession,
} from "../controllers/session.controller.js";

import {
    validateCreateSession,
    validateSessionId,
    validateEvent
} from "../middleware/validation.js";

const router = Router();

router.post(
    "/",
    validateCreateSession,
    createSession
);

router.get(
    "/:id",
    validateSessionId,
    getSession
);

router.post(
    "/:id/event",
    validateSessionId,
    validateEvent,
    addEvent
);

router.get(
    "/:id/finish",
    validateSessionId,
    finishSession
);

export default router;