import express, { type NextFunction, type Request, type Response } from 'express';
import { pool } from '../db.js';
import { authMiddleware } from "../middleware/authCheck.js";

const router = express.Router();

//TESTED AND WORKING
router.get('/', authMiddleware, async (req: Request, res: Response, next: NextFunction) => {
    const userId = req.userId;
    try{
        const response = await pool.query("SELECT * FROM sessions WHERE user_id = $1", [userId]);
        res.status(200).json(response.rows);
    }catch(err) {
        console.error(err);
        res.status(500).json({ error: "Internal Server Error" });
    }
});

router.get('/:id', authMiddleware, async (req: Request, res: Response, next: NextFunction) => {
    const sessionId = req.params.id;
    const userId = req.userId;
    try{
        const response = await pool.query("SELECT * FROM sessions WHERE id = $1 AND user_id = $2", [sessionId, userId]);
        if(response.rows.length === 0) {
            return res.status(404).json({ error: "Session not found" });
        }
        return res.status(200).json(response.rows[0]);
    }catch(err) {
        console.error(err);
        res.status(500).json({ error: "Internal Server Error" });
    }
});

export default router;