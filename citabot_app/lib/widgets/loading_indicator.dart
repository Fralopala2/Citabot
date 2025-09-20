import 'package:flutter/material.dart';

class LoadingIndicator extends StatelessWidget {
  final String message;
  final bool showSpinner;
  final Color? color;

  const LoadingIndicator({
    super.key,
    required this.message,
    this.showSpinner = true,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showSpinner)
            SizedBox(
              width: 40,
              height: 40,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                valueColor: AlwaysStoppedAnimation<Color>(
                  color ?? Colors.deepPurple,
                ),
              ),
            ),
          if (showSpinner) const SizedBox(height: 16),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              color: color ?? Colors.deepPurple,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class LoadingOverlay extends StatelessWidget {
  final String message;
  final Widget child;
  final bool isLoading;

  const LoadingOverlay({
    super.key,
    required this.message,
    required this.child,
    required this.isLoading,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        if (isLoading)
          Container(
            color: Colors.black.withValues(alpha: 0.3),
            child: Center(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: LoadingIndicator(message: message),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class SearchingIndicator extends StatefulWidget {
  final String message;

  const SearchingIndicator({super.key, required this.message});

  @override
  State<SearchingIndicator> createState() => _SearchingIndicatorState();
}

class _SearchingIndicatorState extends State<SearchingIndicator>
    with TickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat();
    _animation = Tween<double>(begin: 0, end: 1).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.deepPurple.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.deepPurple.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          AnimatedBuilder(
            animation: _animation,
            builder: (context, child) {
              return Transform.rotate(
                angle: _animation.value * 2 * 3.14159,
                child: const Icon(
                  Icons.refresh,
                  color: Colors.deepPurple,
                  size: 20,
                ),
              );
            },
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              widget.message,
              style: const TextStyle(
                color: Colors.deepPurple,
                fontSize: 14,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
