import express, { type NextFunction, type Request, type Response } from 'express';
import { pool } from '../db.js';

const router = express.Router();

//TESTED AND WORKING
router.get('/', async (req: Request, res: Response, next: NextFunction) => {
    //const userId = req.userId;
    const userId = "11111111-1111-1111-1111-111111111111";
    try{
        const response = await pool.query("SELECT * FROM sessions WHERE user_id = $1", [userId]);
        res.status(200).json(response.rows);
    }catch(err) {
        console.error(err);
        res.status(500).json({ error: "Internal Server Error" });
    }
});

export default router;