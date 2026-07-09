-- AlterTable
ALTER TABLE `order` MODIFY `auth` LONGTEXT NULL;

-- AlterTable
ALTER TABLE `user` MODIFY `token` LONGTEXT NOT NULL;
