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
        prompt,
        duration
    } = req.body;

    if (!prompt) {
        return res.status(400).json({
            error: "Session prompt is required"
        });
    }

    if (typeof prompt !== "string") {
        return res.status(400).json({
            error: "Session prompt must be a string"
        });
    }

    if (
        duration === undefined ||
        duration === null
    ) {
        return res.status(400).json({
            error: "Session duration is required"
        });
    }

    if (
        typeof duration !== "number" ||
        duration <= 0
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
    const { timestamp, event_type } = req.body;

    if(!timestamp || !event_type ) {
        return res.status(400).json({
            error: "Event must have a timestamp and type"
        });
    }

    next();
}