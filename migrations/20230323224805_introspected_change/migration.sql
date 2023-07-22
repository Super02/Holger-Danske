-- CreateTable
CREATE TABLE "BotStorage" (
    "id" SERIAL NOT NULL,
    "ticket_amount" INTEGER NOT NULL DEFAULT 0,
    "last_ping" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "BotStorage_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Ticket" (
    "id" SERIAL NOT NULL,
    "reporter" TEXT NOT NULL,
    "reported" TEXT NOT NULL,
    "evidence" TEXT NOT NULL,
    "reason" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "staffId" INTEGER NOT NULL,
    "punishment" TEXT NOT NULL,
    "messageId" TEXT NOT NULL,
    "additionalInfo" TEXT,
    "completedIn" INTEGER,

    CONSTRAINT "Ticket_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AgeVerification" (
    "id" SERIAL NOT NULL,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "time_limit" TIMESTAMP(3),
    "messageId" TEXT,
    "discord_id" TEXT NOT NULL,
    "verified" BOOLEAN NOT NULL DEFAULT false,
    "verified_by" TEXT,
    "requested_by" TEXT NOT NULL,

    CONSTRAINT "AgeVerification_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ReportTicket" (
    "id" SERIAL NOT NULL,
    "reporter" TEXT NOT NULL,
    "reported" TEXT NOT NULL,
    "evidence" TEXT NOT NULL,
    "reason" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "messageId" TEXT NOT NULL,
    "additionalInfo" TEXT,
    "claimed_by" TEXT,

    CONSTRAINT "ReportTicket_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AppealTicket" (
    "id" SERIAL NOT NULL,
    "discord_id" TEXT NOT NULL,
    "reason" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "messageId" TEXT NOT NULL,
    "appeal" TEXT NOT NULL,
    "notes" TEXT,
    "claimed_by" TEXT,
    "username" TEXT NOT NULL,

    CONSTRAINT "AppealTicket_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Staff" (
    "id" SERIAL NOT NULL,
    "discord_id" TEXT NOT NULL,

    CONSTRAINT "Staff_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "User" (
    "id" SERIAL NOT NULL,
    "discord_id" TEXT NOT NULL,
    "dm_blacklist" BOOLEAN NOT NULL DEFAULT false,
    "last_appeal" TEXT,
    "ticket_blacklist" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "quota_exception" (
    "id" SERIAL NOT NULL,
    "staffId" INTEGER NOT NULL,
    "start_date" TIMESTAMP(3) NOT NULL,
    "end_date" TIMESTAMP(3) NOT NULL,
    "reason" TEXT NOT NULL,
    "approved" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "quota_exception_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "strikes" (
    "id" SERIAL NOT NULL,
    "staffId" INTEGER NOT NULL,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "reason" TEXT NOT NULL,
    "moderator" TEXT NOT NULL,
    "message_id" TEXT NOT NULL,

    CONSTRAINT "strikes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "warning" (
    "id" SERIAL NOT NULL,
    "staffId" INTEGER NOT NULL,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "reason" TEXT NOT NULL,
    "moderator" TEXT NOT NULL,
    "message_id" TEXT NOT NULL,

    CONSTRAINT "warning_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "AgeVerification_messageId_key" ON "AgeVerification"("messageId");

-- CreateIndex
CREATE UNIQUE INDEX "ReportTicket_messageId_key" ON "ReportTicket"("messageId");

-- CreateIndex
CREATE UNIQUE INDEX "AppealTicket_messageId_key" ON "AppealTicket"("messageId");

-- CreateIndex
CREATE UNIQUE INDEX "Staff_discord_id_key" ON "Staff"("discord_id");

-- CreateIndex
CREATE UNIQUE INDEX "User_discord_id_key" ON "User"("discord_id");

-- CreateIndex
CREATE UNIQUE INDEX "strikes_message_id_key" ON "strikes"("message_id");

-- CreateIndex
CREATE UNIQUE INDEX "warning_message_id_key" ON "warning"("message_id");

-- AddForeignKey
ALTER TABLE "Ticket" ADD CONSTRAINT "Ticket_staffId_fkey" FOREIGN KEY ("staffId") REFERENCES "Staff"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "quota_exception" ADD CONSTRAINT "quota_exception_staffId_fkey" FOREIGN KEY ("staffId") REFERENCES "Staff"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "strikes" ADD CONSTRAINT "strikes_staffId_fkey" FOREIGN KEY ("staffId") REFERENCES "Staff"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "warning" ADD CONSTRAINT "warning_staffId_fkey" FOREIGN KEY ("staffId") REFERENCES "Staff"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
