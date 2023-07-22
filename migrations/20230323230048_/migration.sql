/*
  Warnings:

  - A unique constraint covering the columns `[discord_id]` on the table `AgeVerification` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "AgeVerification_discord_id_key" ON "AgeVerification"("discord_id");
