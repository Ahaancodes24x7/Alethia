import express, { type NextFunction, type Request, type Response } from 'express';
import sessionRouter from './routes/session.js';
import dashboardRouter from './routes/dashboard.js';
import authRouter from './routes/auth.js';
import { pool } from "./db.js";
import {redis} from "./redis.js";
import {Worker} from "bullmq";
import {EventEmitter} from "events";
import axios from "axios";

const app = express();
const PORT = 3000;

app.use(express.json());

app.use('/session', sessionRouter);
app.use('/dashboard', dashboardRouter);
app.use('/auth', authRouter);

export const eventEmitter = new EventEmitter();
const connection = {
    host: "localhost",
    port: 6379,
};
const worker = new Worker("analysis", async (job) => {
    const sessionId = job.data.id;
    console.log(sessionId);

    try{
        const sessionData = await redis.get(sessionId);
        const events = JSON.parse(sessionData!).events;
        const report = await axios.post("http://localhost:8000/predict", {
            session_id: sessionId,
            events: events
        });
        return report;
    }
    catch (error) {
        console.error("Error occurred while making API call:", error);
        throw error;
    }
    
}, {connection});

worker.on("completed", (job, report) => {
    eventEmitter.emit(`job:completed:${job.data.id}`, { sessionId: job.data.id, report });
});

worker.on("failed", (job, err) => {
    if(!job) return;
    eventEmitter.emit(`job:failed:${job.data.id}`, { error: err });
})

app.get('/', (req: Request, res: Response, next: NextFunction) => {
    res.send('Hello, World!');
});

app.listen(PORT, async () => {
    const result = await pool.query("SELECT NOW()");
    console.log(result.rows);
    console.log(`Server is running on port ${PORT}`);
});