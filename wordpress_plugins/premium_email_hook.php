<?php
/**
 * X Post Generator プレミアムコード自動送信
 * 場所: public_html/www.ins-japan.com/wp-content/mu-plugins/premium_email_hook.php
 */

// Simple Membership の会員登録完了時にフック
add_action('swpm_registration_was_successful', 'xpost_send_membership_email', 10, 1);

function xpost_send_membership_email($member_id) {
    $member = SwpmMemberUtils::get_user_by_id($member_id);
    if (!$member) return;

    $email = sanitize_email($member->email);
    $name = sanitize_text_field($member->first_name ?: 'お客様');
    $level_id = intval($member->membership_level);

    // 有料会員レベルIDリスト（実際のIDに変更すること）
    $paid_levels = array(2, 3, 4); // ← Render環境変数 PAID_LEVEL_IDS で管理推奨
    $is_paid = in_array($level_id, $paid_levels);

    if ($is_paid) {
        // 有料会員：プレミアムコード付きメール
        $premium_code = get_option('xpost_premium_code', 'XPOST-PRO-2024');
        $subject = '【X Post Generator】プレミアムアクセスコードのご案内';
        $body = "{$name} 様\n\n";
        $body .= "有料会員へのご登録ありがとうございます。\n\n";
        $body .= "━━━━━━━━━━━━━━━━━━━━\n";
        $body .= "  プレミアムアクセスコード\n\n";
        $body .= "  【 {$premium_code} 】\n\n";
        $body .= "━━━━━━━━━━━━━━━━━━━━\n\n";
        $body .= "このコードを X Post Generator の「⚙️ 設定」タブに入力すると、\n";
        $body .= "複数アカウントの登録・切り替え機能が使えるようになります。\n\n";
        $body .= "▼ X Post Generator にアクセス\n";
        $body .= "https://www.ins-japan.com/x-post-generator/\n\n";
        $body .= "▼ 有料会員向け完全マニュアル\n";
        $body .= "https://bep-post-generator.onrender.com/manual/paid\n\n";
        $body .= "ご不明な点はお気軽にご連絡ください。\n";
        $body .= "X Post Generator 運営チーム";
    } else {
        // 無料会員：基本マニュアルリンクのみ
        $subject = '【X Post Generator】ご登録ありがとうございます';
        $body = "{$name} 様\n\n";
        $body .= "2週間無料お試し登録ありがとうございます。\n\n";
        $body .= "▼ X Post Generator にアクセス\n";
        $body .= "https://www.ins-japan.com/x-post-generator/\n\n";
        $body .= "▼ 基本マニュアル\n";
        $body .= "https://bep-post-generator.onrender.com/manual/free\n\n";
        $body .= "使い方でご不明な点はマニュアルをご参照ください。\n";
        $body .= "有料会員にアップグレードすると複数アカウント機能が使えます。\n\n";
        $body .= "▼ 有料会員へのアップグレード\n";
        $body .= "https://www.ins-japan.com/sign-up-for-a-paid-membership/\n\n";
        $body .= "X Post Generator 運営チーム";
    }

    $headers = array('Content-Type: text/plain; charset=UTF-8');
    wp_mail($email, $subject, $body, $headers);
}
