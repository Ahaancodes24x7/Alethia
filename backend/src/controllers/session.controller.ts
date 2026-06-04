import { Request, Response } from "express";
import { v4 as uuidv4 } from "uuid";
import { pool } from "../db.js";
import {redis} from "../redis.js";
import { analysisQueue } from "../queue/analysis.js";
import {eventEmitter} from "../index.js";

//replacement for redis for now
type CacheEntry = {
    prompt: string;
    startTime: Date;
    duration: number | string;
    userId: string;
    events: any[];
}

interface SessionParams {
    id: string;
}

//TESTED AND WORKING
export async function createSession(req: Request,res: Response) {
    const sessionPrompt = req.body.prompt;
    const sessionDuration = req.body.duration;
    //const userId = req.body.userId;

    const sessionId = uuidv4();
    const currentSession: CacheEntry = {
        "prompt": sessionPrompt,
        "startTime": new Date(),
        "duration": sessionDuration,
        "userId": "11111111-1111-1111-1111-111111111111",
        "events": []
    }
    
    redis.set(sessionId, JSON.stringify(currentSession)); 

    return res.status(201).json({
        message: "Session created",
        id: sessionId
    });
}

//TESTED AND WORKING
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

//TESTED AND WORKING
export async function addEvent(
    req: Request<SessionParams>,
    res: Response
) {
    const sessionId = req.params.id;

    const eventPayload = req.body.eventPayload;

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

//const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

//TESTED AND WORKING
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
    res.write("data: processing\n\n");

    analysisQueue.add("process", { "id": sessionId });

    eventEmitter.once(`job:completed:${sessionId}`, (data) => {
        console.log(data.report);
        redis.get(sessionId, async (err, result) => {
            if (err) {
                console.error("Error fetching session from Redis:", err);
                return;
            }
            if(!result) {
                console.error("Session not found in Redis");
                return;
            }
            const { userId, prompt, startTime }: CacheEntry = JSON.parse(result);

            try{
                const result = await pool.query(
                    "INSERT INTO sessions (id, user_id, prompt, start_time, end_time, report) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
                    [sessionId, userId, prompt, startTime, new Date(), data.report]
                );
                const returnResponse = JSON.stringify(result.rows[0]);
                redis.del(sessionId);
                res.write(`data: ${returnResponse}\n\n`);
                res.end()
            } catch (err) {
                console.error(err);
                res.write("data: Error inserting session into database\n\n");
                res.end();
            }
        });
    });

    eventEmitter.once(`job:failed:${sessionId}`, (data) => {
        console.log(data.error);
        res.write("data: failed\n\n");
        res.end();
    });
}