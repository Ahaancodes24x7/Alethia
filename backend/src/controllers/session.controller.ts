import { Request, Response } from "express";
import { v4 as uuidv4 } from "uuid";
import { pool } from "../db.js";
import {redis} from "../redis.js";
import { analysisQueue } from "../queue/analysis.js";
import {eventEmitter} from "../index.js";

//replacement for redis for now
type CacheEntry = {
    prompt: string;
    startTime: number;
    duration: number | string;
    userId: string;
    events: any[];
}

interface SessionParams {
    id: string;
}

export async function createSession(req: Request,res: Response) {
    const sessionPrompt = req.body.prompt;
    const sessionDuration = req.body.duration;
    //const userId = req.body.userId;

    const sessionId = uuidv4();
    const currentSession: CacheEntry = {
        "prompt": sessionPrompt,
        "startTime": Date.now(),
        "duration": sessionDuration,
        "userId": "11111111-1111-1111-1111-111111111111",
        "events": []
    }
    
    redis.set(sessionId, JSON.stringify(currentSession)); 

    return res.status(201).json({
        message: "Session created",
    });
}

export async function getSession(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    redis.get(sessionId, (err, result) => {
        if (err) {
            console.error("Error fetching session from Redis:", err);
            return res.status(500).json({ error: "Internal Server Error" });
        }
        if (!result) {
            return res.status(404).json({ error: "Session not found" });
        }
        const sessionData: CacheEntry = JSON.parse(result);
        return res.status(200).json(sessionData);
    }); 
}

export async function addEvent(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    const eventPayload = req.body.payload;

    redis.get(sessionId, (err, result) => {
        if (err) {
            console.error("Error fetching session from Redis:", err);
            return res.status(500).json({ error: "Internal Server Error" });
        }
        if (!result) {
            return res.status(404).json({ error: "Session not found" });
        }
        const sessionData: CacheEntry = JSON.parse(result);
        sessionData.events.push(eventPayload);
        redis.set(sessionId, JSON.stringify(sessionData));
        return res.status(200).json({"message": "Event Added"});
    });
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export async function finishSession(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    console.log("called");

    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();
    res.write("data: processing\n");

    analysisQueue.add("process", { "id": sessionId });

    eventEmitter.once(`job:completed:${sessionId}`, (data) => {
        console.log(data.report);
        res.write("data: event completed\n");
        res.end();
    });

    eventEmitter.once(`job:failed:${sessionId}`, (data) => {
        console.log(data.error);
        res.write("data: event failed\n");
        res.end();
    });
}