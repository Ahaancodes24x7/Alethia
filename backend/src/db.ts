import { Pool } from "pg";

import dotenv from "dotenv";
dotenv.config();

export const pool = new Pool({
    user: process.env.DATABASE_USER,
    password: process.env.DATABASE_PASSWORD,
    host: "localhost",
    port: 5432,
    database: process.env.DATABASE_NAME
});