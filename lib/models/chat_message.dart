enum MessageSender {
  investigator,
  witness,
  system,
}

class ChatMessage {
  final String id;
  String text;
  final MessageSender sender;
  final DateTime timestamp;
  final bool isEditable;
  final int? questionIndex;

  ChatMessage({
    required this.id,
    required this.text,
    required this.sender,
    required this.timestamp,
    this.isEditable = false,
    this.questionIndex,
  });

  bool get isWitness => sender == MessageSender.witness;
  bool get isInvestigator => sender == MessageSender.investigator;
  bool get isSystem => sender == MessageSender.system;

  ChatMessage copyWith({
    String? text,
    bool? isEditable,
  }) {
    return ChatMessage(
      id: id,
      text: text ?? this.text,
      sender: sender,
      timestamp: timestamp,
      isEditable: isEditable ?? this.isEditable,
      questionIndex: questionIndex,
    );
  }
}

