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
import { authMiddleware } from "../middleware/authCheck.js";
import {rateLimit} from "../middleware/rateLimit.js"

const router = Router();

router.use(authMiddleware);
router.use(rateLimit);

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