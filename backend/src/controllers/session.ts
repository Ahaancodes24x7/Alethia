import { Request, Response } from "express";
import { v4 as uuidv4 } from "uuid";
import { pool } from "../db.js";


//replacement for redis for now
type CacheEntry = {
    prompt: string;
    startTime: number;
    duration: number | string;
    userId: string;
    events: any[];
};
const tmp_cache: Record<string, CacheEntry> = {};

interface SessionParams {
    id: string;
}

export async function createSession(req: Request,res: Response) {
    const sessionPrompt = req.body.sessionPrompt;
    const sessionDuration = req.body.sessionDuration;
    //const userId = req.body.userId;

    const sessionId = uuidv4();
    tmp_cache[sessionId] = {
        "prompt": sessionPrompt,
        "startTime": Date.now(),
        "duration": sessionDuration,
        "userId": "11111111-1111-1111-1111-111111111111",
        "events": []
    };
    

    return res.status(201).json({
        message: "Session created",
        sessionPrompt,
        sessionDuration
    });
}

export async function getSession(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    // db query goes here 

    return res.status(200).json(tmp_cache[sessionId]);
}

export async function addEvent(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    const eventPayload = req.body.eventPayload;

    tmp_cache[sessionId].events.push(eventPayload);

    return res.status(200).json({
        sessionId,
        eventPayload
    });
}

export async function finishSession(
    req: Request<SessionParams>,
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