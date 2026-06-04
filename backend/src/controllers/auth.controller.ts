import { type Request, type Response } from "express";
import { pool } from "../db.js";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import { v4 as uuidv4 } from "uuid";

import dotenv from "dotenv";
dotenv.config();

export async function signupHandler(req: Request, res: Response) {
    const { email, name, password } = req.body;

    //no empty inputs
    if (!email || !name || !password) {
        return res.status(400).json({ error: "Email, name and password are required" });
    }
    //valid types
    if(typeof email !== "string" || typeof name !== "string" || typeof password !== "string") {
        return res.status(400).json({ error: "Email, name and password must be strings" });
    }
    //email unique check
    const emailCheck = await pool.query("SELECT id FROM users WHERE email = $1", [email]);
    if (emailCheck.rows.length > 0) return res.status(400).json({ error: "Email already in use" });

    try {
        const hashedPassword = await bcrypt.hash(password, Math.floor(Math.random() * 6) + 10);
        const result = await pool.query(
            "INSERT INTO users (id, email, name, password) VALUES ($1, $2, $3, $4) RETURNING id",
            [uuidv4(), email, name, hashedPassword]
        );
        const userId = result.rows[0].id;
        res.status(201).json({ message: "User created", id: userId });
    } catch (error) {
        console.error("Error creating user:", error);
        res.status(500).json({ error: "Internal server error" });
    }
}

export async function loginHandler(req: Request, res: Response) {
     const { email, password } = req.body;

    //no empty inputs
    if (!email || !password) {
        return res.status(400).json({ error: "Email and password are required" });
    }
    //valid types
    if(typeof email !== "string" || typeof password !== "string") {
        return res.status(400).json({ error: "Email and password must be strings" });
    }

    try {
        const result = await pool.query("SELECT id, password FROM users WHERE email = $1", [email]);
        if (result.rows.length === 0) {
            return res.status(401).json({ error: "Invalid email or password" });
        }

        const user = result.rows[0];
        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return res.status(401).json({ error: "Invalid email or password" });
        }
        const token = jwt.sign({id: user.id}, process.env.JWT_SECRET!, {expiresIn: "4h"});

        res.status(200).json({token});
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: "Internal server error" });
    }
}