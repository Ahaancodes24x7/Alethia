import { Request, Response, NextFunction } from "express";

type SessionParams = {
    id: string;
};

export function validateSessionId(
    req: Request<SessionParams>,
    res: Response,
    next: NextFunction
) {
    const sessionId = req.params.id;

    if (!sessionId) {
        return res.status(400).json({
            error: "Session id is required"
        });
    }

    next();
}

export function validateCreateSession(
    req: Request,
    res: Response,
    next: NextFunction
) {
    const {
        sessionPrompt,
        sessionDuration
    } = req.body;

    if (!sessionPrompt) {
        return res.status(400).json({
            error: "Session prompt is required"
        });
    }

    if (typeof sessionPrompt !== "string") {
        return res.status(400).json({
            error: "Session prompt must be a string"
        });
    }

    if (
        sessionDuration === undefined ||
        sessionDuration === null
    ) {
        return res.status(400).json({
            error: "Session duration is required"
        });
    }

    if (
        typeof sessionDuration !== "number" ||
        sessionDuration <= 0
    ) {
        return res.status(400).json({
            error: "Session duration must be a positive number"
        });
    }

    next();
}

export function validateEvent(
    req: Request<SessionParams>,
    res: Response,
    next: NextFunction
) {
    const { eventPayload } = req.body;

    if (!eventPayload) {
        return res.status(400).json({
            error: "Event payload is required"
        });
    }

    if (
        typeof eventPayload !== "object" ||
        Array.isArray(eventPayload)
    ) {
        return res.status(400).json({
            error: "Event payload must be an object"
        });
    }

    next();
}