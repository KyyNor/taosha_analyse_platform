#!/bin/bash

# 批量替换confirm调用的脚本
# 用法: ./batch_replace_confirm.sh

FRONTEND_DIR="/home/kyynor/code/taosha_workspace/taosha_analyse_platform/frontend"

# 需要处理的文件列表
FILES=(
    "$FRONTEND_DIR/app/(main)/metadata/tables/[tableId]/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/themes/[themeId]/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/themes/new/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/relations/[configId]/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/relations/new/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/prompt-templates/[templateId]/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/prompt-templates/new/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/glossary/[termId]/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/glossary/new/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/fine-reports/[reportId]/page.tsx"
    "$FRONTEND_DIR/app/(main)/metadata/fine-reports/new/page.tsx"
    "$FRONTEND_DIR/app/(main)/fraudhunter/risk-control-models/[id]/page.tsx"
    "$FRONTEND_DIR/app/(main)/fraudhunter/indicators/[id]/page.tsx"
    "$FRONTEND_DIR/app/(main)/fraudhunter/indicators/new/page.tsx"
    "$FRONTEND_DIR/app/(main)/fraudhunter/dry-run/[id]/page.tsx"
)

# 检查文件是否存在
for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "警告: 文件不存在: $file"
    fi
done

echo "开始批量替换confirm调用..."

# 对每个文件进行处理
for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "处理文件: $file"

        # 检查是否已经导入了useConfirmDialog
        if ! grep -q "useConfirmDialog" "$file"; then
            # 找到import语句的末尾，添加useConfirmDialog导入
            sed -i '/^import.*from.*\.js"$/a import { useConfirmDialog } from "@/components/ui/confirm-dialog";' "$file"
        fi

        # 添加useConfirmDialog hook
        if grep -q "const \[.*\] = useState" "$file"; then
            sed -i '0,/const \[.*\] = useState.*/a\  const { confirm, DialogComponent } = useConfirmDialog();' "$file"
        fi

        # 替换confirm调用 - 匹配各种模式
        # 模式1: if (confirm("...")) {
        sed -i 's/if (confirm(\([^)]*\)))/if (false) \/\/ 替换为confirm调用/g' "$file"
        sed -i 's/if (confirm(\([^)]*\)))/confirm({ title: "确认", description: \1, onConfirm: () => {, variant: "default" })/g' "$file"

        # 模式2: if (!confirm("...")) return;
        sed -i 's/if (!confirm(\([^)]*\))) return;/confirm({ title: "确认", description: \1, onConfirm: () => {}, variant: "default" }); return;/g' "$file"

        # 添加DialogComponent到return语句
        if grep -q "return (" "$file" && ! grep -q "<DialogComponent />" "$file"; then
            sed -i 's/return (/return (<>\n      <DialogComponent \/>\n      /' "$file"
        fi

        # 在文件末尾添加闭合标签
        if grep -q "<DialogComponent />" "$file" && ! grep -q "<\/>" "$file"; then
            sed -i '$a\    <\/>' "$file"
        fi

        echo "完成处理: $file"
    fi
done

echo "批量替换完成！"
echo "请注意：脚本可能需要手动调整一些复杂的确认逻辑。"