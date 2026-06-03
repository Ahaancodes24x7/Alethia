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

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export async function finishSession(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    console.log("called");

    // add finished session info to database
    // add session id to queue for processing
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();
    res.write("data: session processing\n");

    await delay(3000);

    res.write("data: event completed\n");

    res.end();
}