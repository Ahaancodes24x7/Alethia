import express, { type NextFunction, type Request, type Response } from 'express';
import sessionRouter from './routes/session.js';
import { pool } from "./db.js";

const app = express();
const PORT = 3000;

app.use(express.json());

app.use('/session', sessionRouter); 


app.get('/', (req: Request, res: Response, next: NextFunction) => {
  res.send('Hello, World!');
});

app.listen(PORT, async () => {
    const result = await pool.query("SELECT NOW()");
    console.log(result.rows);
    console.log(`Server is running on port ${PORT}`);
});