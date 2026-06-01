import { Request, Response } from "express";

export async function createSession(
    req: Request,
    res: Response
) {
    const sessionPrompt = req.body.sessionPrompt;
    const sessionDuration = req.body.sessionDuration;

    // db query goes here

    return res.status(201).json({
        message: "Session created",
        sessionPrompt,
        sessionDuration
    });
}

export async function getSession(
    req: Request,
    res: Response
) {
    const sessionId = req.params.id;

    // db query goes here 

    return res.status(200).json({
        sessionId
    });
}

export async function addEvent(
    req: Request,
    res: Response
) {
    const sessionId = req.params.id;

    const eventPayload = req.body.eventPayload;

    // db query goes here

    return res.status(200).json({
        sessionId,
        eventPayload
    });
}

export async function finishSession(
    req: Request,
    res: Response
) {
    const sessionId = req.params.id;

    // db query goes here

    return res.status(200).json({
        message: "Session marked complete",
        sessionId
    });
}

export async function getReport(
    req: Request,
    res: Response
) {
    const sessionId = req.params.id;

    // queue logic goes here

    return res.status(200).json({
        sessionId
    });
}