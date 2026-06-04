import express, { type NextFunction, type Request, type Response } from 'express';

const router = express.Router();

router.get('/', (req: Request, res: Response, next: NextFunction) => {
    res.status(200).json({ message: 'Welcome to the dashboard!' });
});

router.get

export default router;