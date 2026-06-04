import express, { type NextFunction, type Request, type Response } from 'express';
import jwt from "jsonwebtoken";
import dotenv from "dotenv";
dotenv.config();

export async function authMiddleware(req: Request, res: Response, next: NextFunction){
    try{
        if(!req.headers.authorization) {
            return res.status(401).send("User Unauthorized");
        }
        const decoded = jwt.verify(req.headers.authorization, process.env.JWT_SECRET!) as {id: string};
        req.userId = decoded.id;
        next();
    }catch(err){
        return res.status(401).send("User Unauthorized");
    }
}