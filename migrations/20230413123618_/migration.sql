-- AlterTable
ALTER TABLE "Ticket" ADD COLUMN     "multiplier" INTEGER NOT NULL DEFAULT 1;

-- CreateTable
CREATE TABLE "TicketPurges" (
    "id" SERIAL NOT NULL,
    "start" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "end" TIMESTAMP(3) NOT NULL,
    "multiplier" INTEGER NOT NULL,
    "created_by" TEXT NOT NULL,

    CONSTRAINT "TicketPurges_pkey" PRIMARY KEY ("id")
);
